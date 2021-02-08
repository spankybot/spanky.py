import logging
import asyncio
import glob
import os
import importlib
import asyncio

from discord import File
from spanky.plugin.reloader import PluginReloader
from spanky.plugin.hook_logic import find_hooks, find_tables
from spanky.plugin.event import EventType, OnStartEvent, OnReadyEvent, OnConnReadyEvent
from spanky.inputs.console import EventMessage
from spanky.plugin.hook_parameters import map_params

logger = logging.getLogger('spanky')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


class PluginManager():
    def __init__(self, path_list, bot, db):
        self.modules = []
        self.plugins = {}
        self.commands = {}
        self.event_type_hooks = {}
        self.regex_hooks = []
        self.sieves = []
        self.catch_all_triggers = []
        self.run_on_ready = []
        self.run_on_conn_ready = []
        self.raw_triggers = []
        self.bot = bot
        self.db = db

        self.loop = asyncio.get_event_loop()

        # Load each path
        for path in path_list:
            self.plugins.update(self.load_plugins(path))

        self.reloader = {}
        for path in path_list:
            self.reloader[path] = PluginReloader(self)
            self.reloader[path].start([path])

        for plugin in self.plugins.values():
            self.finalize_plugin(plugin)

    def finalize_plugin(self, plugin):
        plugin.create_tables(self.db)

        # run on_start hooks
        for on_start_hook in plugin.run_on_start:
            success = self.launch(OnStartEvent(bot=self.bot, hook=on_start_hook))
            if not success:
                logger.warning("Not registering hooks from plugin {}: on_start hook errored".format(plugin.name))

                # unregister databases
                plugin.unregister_tables(self.db)
                return

        # run on_ready hooks if bot ready
        if self.bot.is_ready:
            # Run the on ready hooks per server
            for server in self.bot.backend.get_servers():
                for on_ready_hook in plugin.run_on_ready:
                    self.launch(OnReadyEvent(
                        bot=self.bot,
                        hook=on_ready_hook,
                        permission_mgr=self.bot.get_pmgr(server.id),
                        server=server))

            # Run connection ready hooks too
            for on_conn_ready_hook in plugin.run_on_conn_ready:
                self.launch(OnConnReadyEvent(
                    bot=self.bot,
                    hook=on_conn_ready_hook))


        for periodic_hook in plugin.periodic:
            logger.debug("Loaded {}".format(repr(periodic_hook)))

        # register commands
        for command_hook in plugin.commands:
            for alias in command_hook.aliases:
                if alias in self.commands:
                    logger.warning(
                        "Plugin {} attempted to register command {} which was already registered by {}. "
                        "Ignoring new assignment.".format(plugin.name, alias, self.commands[alias].plugin.name))
                else:
                    self.commands[alias] = command_hook
            logger.debug("Loaded {}".format(repr(command_hook)))

        # register raw hooks
        for raw_hook in plugin.raw_hooks:
            if raw_hook.is_catch_all():
                self.catch_all_triggers.append(raw_hook)
            else:
                for trigger in raw_hook.triggers:
                    if trigger in self.raw_triggers:
                        self.raw_triggers[trigger].append(raw_hook)
                    else:
                        self.raw_triggers[trigger] = [raw_hook]
            logger.debug("Loaded {}".format(repr(raw_hook)))

        # register events
        for event_hook in plugin.events:
            for event_type in event_hook.types:
                if event_type in self.event_type_hooks:
                    self.event_type_hooks[event_type].append(event_hook)
                else:
                    self.event_type_hooks[event_type] = [event_hook]
            logger.debug("Loaded {}".format(repr(event_hook)))

        # register regexps
        for regex_hook in plugin.regexes:
            for regex_match in regex_hook.regexes:
                self.regex_hooks.append((regex_match, regex_hook))
            logger.debug("Loaded {}".format(repr(regex_hook)))

        # register sieves
        for sieve_hook in plugin.sieves:
            self.sieves.append(sieve_hook)

        # register on connection ready hooks
        for on_ready_hook in plugin.run_on_ready:
            self.run_on_ready.append(on_ready_hook)

        # register on ready hooks
        for on_conn_ready_hook in plugin.run_on_conn_ready:
            self.run_on_conn_ready.append(on_conn_ready_hook)

        # sort sieve hooks by priority
        self.sieves.sort(key=lambda x: x.priority)

    def _prepare_parameters(self, hook, event):
        """
        Prepares arguments for the given hook

        :type hook: cloudbot.plugin.Hook
        :type event: cloudbot.event.Event
        :rtype: list
        """
        parameters = []

        # Is only none for PMs
        if hasattr(event, "permission_mgr") and event.permission_mgr:
            if "storage" in hook.required_args:
                stor_name = hook.plugin.name.replace(".py", "").replace("/","_")
                event.storage = event.permission_mgr.get_plugin_storage(stor_name + ".json")

            if "storage_loc" in hook.required_args:
                event.storage_loc = \
                    event.permission_mgr.get_data_location(
                        hook.plugin.name.replace(".py", "").replace("/","_"))

        if "cmd_args" in hook.required_args and hook.param_list is not None:
            event.cmd_args = map_params(event.text, hook.param_list)
        else:
            event.cmd_args = {}

        for required_arg in hook.required_args:
            if hasattr(event, required_arg):
                value = getattr(event, required_arg)
                parameters.append(value)
            elif hasattr(event.event, required_arg):
                value = getattr(event.event, required_arg)
                parameters.append(value)
            else:
                logger.error("Plugin {} asked for invalid argument '{}', cancelling execution!"
                             .format(hook.description, required_arg))
                print(dir(event))
                print(dir(event.event))
                return None
        return parameters

    def _execute_hook(self, hook, event):
        event.prepare()

        parameters = self._prepare_parameters(hook, event)
        if parameters is None:
            return None

        # shitty workaround
        async def call_func():
            try:
                await hook.function(*parameters)
            except:
                import traceback; traceback.print_exc()

        if not asyncio.iscoroutinefunction(hook.function):
            return hook.function(*parameters)
        else:
            asyncio.run_coroutine_threadsafe(call_func(), self.bot.loop)
            return None

    def execute_hook(self, hook, event):
        """
        Runs the specific hook with the given bot and event.

        Returns False if the hook errored, True otherwise.
        """

        out = self._execute_hook(hook, event)
        
        if out is not None:
            if isinstance(out, (list, tuple)):
                # if there are multiple items in the response, return them on multiple lines
                event.reply(*out)
            elif isinstance(out, File):
                # shitty workaround
                async def call_func():
                    try:
                        await event.event.async_send_file(out)
                    except:
                        import traceback; traceback.print_exc()
                asyncio.run_coroutine_threadsafe(call_func(), self.bot.loop)
            else:
                event.reply(str(out))

        return (True)

    def correct_format(self, hook, text):
        """Check if the request has the required format"""
        if hook.format:
            if len(hook.format.split()) == len(text.split()):
                return True
            else:
                return False
        else:
            return True

        return False

    def launch(self, launch_event):
        """
        Dispatch a given event to a given hook using a given bot object.
        Returns False if the hook didn't run successfully, and True if it ran successfully.
        """

        hook = launch_event.hook

        if hook.type in ("command") and not launch_event.event.is_pm:
            # Run hooks on only the servers where they should run
            if launch_event.hook.server_id and not launch_event.hook.has_server_id(str(launch_event.event.server.id)):
                return

            # Ask the sieves to validate our command
            for sieve in self.sieves:
                args = {"bot": self.bot, "bot_event":launch_event}
                if "storage" in sieve.required_args:
                    stor_name = sieve.plugin.name.replace(".py", "").replace("/","_")
                    storage = launch_event.permission_mgr.get_plugin_storage(stor_name + ".json")
                    args["storage"] = storage
                can_run, msg = sieve.function(**args)
                if msg:
                    launch_event.event.reply(msg, timeout=15)
                if not can_run:
                    return

            if not self.correct_format(hook, launch_event.text):
                func_doc = hook.function.__doc__

                msg = "Invalid format"

                if func_doc:
                    msg += ": " + "\n`" + hook.function.__doc__.strip() + "`"
                launch_event.event.reply(msg, timeout=15)
                return

        elif hook.type == "on_ready":
            if launch_event.hook.server_id and not launch_event.hook.has_server_id(launch_event.server.id):
                return

        elif hook.type == "event" and launch_event.event.type == EventType.message:
            if launch_event.event.is_pm:
                return
            if launch_event.hook.server_id and not launch_event.hook.has_server_id(launch_event.event.server.id):
                return

        if hook.single_thread:
            # TODO
            pass
        else:
            # Run the plugin with the message, and wait for it to finish
            result = self.execute_hook(hook, launch_event)

        # Return the result
        return result

    def unload_plugin(self, path):
        """
        Unloads the plugin from the given path, unregistering all hooks from the plugin.

        Returns True if the plugin was unloaded, False if the plugin wasn't loaded in the first place.

        :type path: str
        :rtype: bool
        """

        # make sure this plugin is actually loaded
        if not path in self.plugins:
            print("No such plugin found to unload: %s" % path)
            return False

        # get the loaded plugin
        plugin = self.plugins[path]

        # unregister commands
        for command_hook in plugin.commands:
            for alias in command_hook.aliases:
                if alias in self.commands and self.commands[alias] == command_hook:
                    # we need to make sure that there wasn't a conflict, so we don't delete another plugin's command
                    del self.commands[alias]

        # unregister raw hooks
        for raw_hook in plugin.raw_hooks:
            if raw_hook.is_catch_all():
                self.catch_all_triggers.remove(raw_hook)
            else:
                for trigger in raw_hook.triggers:
                    assert trigger in self.raw_triggers  # this can't be not true
                    self.raw_triggers[trigger].remove(raw_hook)
                    if not self.raw_triggers[trigger]:  # if that was the last hook for this trigger
                        del self.raw_triggers[trigger]

        # unregister events
        for event_hook in plugin.events:
            for event_type in event_hook.types:
                assert event_type in self.event_type_hooks  # this can't be not true
                self.event_type_hooks[event_type].remove(event_hook)
                if not self.event_type_hooks[event_type]:  # if that was the last hook for this event type
                    del self.event_type_hooks[event_type]

        # unregister regexps
        for regex_hook in plugin.regexes:
            for regex_match in regex_hook.regexes:
                self.regex_hooks.remove((regex_match, regex_hook))

        # unregister sieves
        for sieve_hook in plugin.sieves:
            self.sieves.remove(sieve_hook)

        # unregister databases
        plugin.unregister_tables(self.db)

        # remove last reference to plugin
        del self.plugins[plugin.name]

        logger.info("Unloaded all plugins from {}.py".format(plugin.name))

        return True

    def load_plugin(self, fname):
        """
        Load a whole plugin file
        :param fname: file name to load
        """

        # Try unloading the file first
        self.unload_plugin(fname)
        plugin = self._load_plugin(fname)

        if plugin:
            self.plugins[fname] = Plugin(fname, plugin)
            self.finalize_plugin(self.plugins[fname])

    def _load_plugin(self, fname):
        """
        Load a plugin.
        """
        logger.debug("Loading %s" % fname)
        basename = os.path.basename(fname)

        # Build file name
        plugin_name = fname.replace("/", ".").replace(".py", "")

        try:
            # Import the file
            plugin_module = importlib.import_module(plugin_name)

            # If file was previously imported, reload
            if plugin_module in self.modules:
                plugin_module = importlib.reload(plugin_module)

            self.modules.append(plugin_module)

            # Return the imported file
            return plugin_module
        except Exception as e:
            import traceback
            logger.debug("Error loading %s:\n\t%s" %(fname, e))
            traceback.print_exc()
            return None

    def load_plugins(self, path):
        """
        Load plugins from a specified path.
        """
        plugins = glob.iglob(os.path.join(path, '*.py'))
        plugin_dict = {}
        for file in plugins:
            plugin_data = self._load_plugin(file)

            if plugin_data:
                plugin_dict[file] = Plugin(file, plugin_data)

        return plugin_dict

class Plugin():
    def __init__(self, name, module):
        self.name = name
        self.file_name = name # Compat with spanky/plugin/hook_logic code

        self.commands, \
            self.regexes, \
            self.raw_hooks, \
            self.sieves, \
            self.events, \
            self.periodic, \
            self.run_on_start, \
            self.run_on_ready, \
            self.run_on_conn_ready = find_hooks(self, module)

        self.tables = find_tables(module)

    def create_tables(self, db_data):

        if self.tables:
            logger.info("Registering tables for {}".format(self.name))

            for table in self.tables:
                if not (table.exists(db_data.db_engine)):
                    table.create(db_data.db_engine)

    def unregister_tables(self, db_data):
        """
        Unregisters all sqlalchemy Tables registered to the global metadata by this plugin
        """
        if self.tables:
            # if there are any tables
            logger.info("Unregistering tables for {}".format(self.name))

            for table in self.tables:
                db_data.db_metadata.remove(table)
