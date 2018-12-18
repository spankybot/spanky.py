import logging
import asyncio
import glob
import os
import importlib

from spanky.plugin.event import Event
from spanky.plugin.reloader import PluginReloader
from spanky.plugin.hook_logic import find_hooks, find_tables

logger = logging.getLogger('spanky')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


class PluginManager():
    def __init__(self, path_list, db):
        self.modules = []
        self.plugins = {}
        self.commands = {}
        self.event_type_hooks = {}
        self.regex_hooks = []
        self.sieves = []
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
            success = self.launch(Event(hook=on_start_hook))
            if not success:
                logger.warning("Not registering hooks from plugin {}: on_start hook errored".format(plugin.name))

                # unregister databases
                plugin.unregister_tables(self.db)
                return
            
        
        for periodic_hook in plugin.periodic:
            logger.debug("Loaded {}".format(repr(periodic_hook)))

        # register commands
        for command_hook in plugin.commands:
            for alias in command_hook.aliases:
                if alias in self.commands:
                    logger.warning(
                        "Plugin {} attempted to register command {} which was already registered by {}. "
                        "Ignoring new assignment.".format(plugin.title, alias, self.commands[alias].plugin.title))
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
            self._log_hook(sieve_hook)

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
        available_params = {}
        available_params.update(event.__dict__)
        if hasattr(event, "event"):
            available_params.update(event.event.__dict__)
            
        for required_arg in hook.required_args:
            if required_arg in available_params:
                value = getattr(event.event, required_arg)
                parameters.append(value)
            else:
                logger.error("Plugin {} asked for invalid argument '{}', cancelling execution!"
                             .format(hook.description, required_arg))
                return None
        return parameters
    
    def _execute_hook_sync(self, hook, event):
        """
        :type hook: Hook
        :type event: cloudbot.event.Event
        """
        event.prepare()

        parameters = self._prepare_parameters(hook, event)
        if parameters is None:
            return None

        try:
            return hook.function(*parameters)
        finally:
            event.close()
            
    def _execute_hook(self, hook, event):
        """
        Runs the specific hook with the given bot and event.

        Returns False if the hook errored, True otherwise.

        :type hook: cloudbot.plugin.Hook
        :type event: cloudbot.event.Event
        :rtype: bool
        """
        out = self._execute_hook_sync(hook, event)
        if out is not None:
            if isinstance(out, (list, tuple)):
                # if there are multiple items in the response, return them on multiple lines
                event.reply(*out)
            else:
                out = "".join(i for i in out)
                event.reply(str(out))
        return (True)
    
    def launch(self, event):
        """
        Dispatch a given event to a given hook using a given bot object.
        Returns False if the hook didn't run successfully, and True if it ran successfully.
        """
        
        hook = event.hook

        if hook.type not in ("on_start", "periodic"):  # we don't need sieves on on_start hooks.
            for sieve in self.sieves:
                event = self._sieve(sieve, event, hook)
                if event is None:
                    return False

        if hook.single_thread:
            # TODO
            pass
        else:
            # Run the plugin with the message, and wait for it to finish
            result = self._execute_hook(hook, event)

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
        plugin_name = "%s.%s" % (os.path.basename(os.path.dirname(fname)), basename)
        plugin_name = plugin_name.replace(".py", "")

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
        
        self.commands, \
            self.regexes, \
            self.raw_hooks, \
            self.sieves, \
            self.events, \
            self.periodic, \
            self.run_on_start = find_hooks(self, module)
            
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
            logger.info("Unregistering tables for {}".format(self.title))

            for table in self.tables:
                db_data.db_metadata.remove(table)