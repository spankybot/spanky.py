import asyncio
import glob
import os
import importlib

from .reloader import PluginReloader
from .hook_logic import find_hooks
# from .hook_parameters import map_params
from .serverdata import ServerData

from common.event import EventType
# from utils import bot_utils as butils

import utils.time_utils as tutils

import common.log as log
import rpc_client

logger = log.botlog("manager", console_level=log.loglevel.DEBUG)


class PluginManager:
    def __init__(self, path_list, bot):
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

        self.loop = asyncio.get_event_loop()

        # Load each path
        for path in path_list:
            plugins = glob.iglob(os.path.join(path, "*.py"))
            for pfile in plugins:
                self.load_plugin(pfile)

        self.reloader = {}
        for path in path_list:
            self.reloader[path] = PluginReloader(self)
            self.reloader[path].start([path])

        # Current servers
        self._servers = {}  # Map of server id -> ServerData

    def add_new_server(self, server):
        """
        Add a new server to the server list
        """
        if server.id in self._servers.keys():
            raise ValueError(f"{server.id} already in the server list")

        if server.id not in self._servers.keys():
            self._servers[server.id] = ServerData(server)

        return self._servers[server.id]

    def get_server_data(self, server_id):
        """
        Get the server data instance for a server ID
        """
        if server_id not in self._servers.keys():
            raise ValueError(f"{server_id} not in server list")

        return self._servers[server_id]

    async def finalize_plugin(self, plugin):
        # run on_start hooks
        for on_start_hook in plugin.run_on_start:
            try:
                await self.launch_event(on_start_hook, EventType.on_start)
            except:
                import traceback

                traceback.print_exc()
                logger.warning(
                    f"Not registering hooks from plugin {plugin.name}: on_start hook errored"
                )
                return

        # run on_ready hooks if bot ready
        if self.bot._is_ready:
            # Run the on ready hooks per server
            for server in self.bot.backend.get_servers():
                for on_ready_hook in plugin.run_on_ready:
                    pass

        for periodic_hook in plugin.periodic:
            logger.debug("Loaded {}".format(repr(periodic_hook)))

        # register commands
        for command_hook in plugin.commands:
            # Check for duplicates
            if command_hook.name in self.commands.keys():
                logger.debug(f"Duplicate name {command_hook.name}. Skipping")
                continue

            self.commands[command_hook.name] = command_hook
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

        # register on ready hooks
        for on_ready_hook in plugin.run_on_ready:
            self.run_on_ready.append(on_ready_hook)

        # sort sieve hooks by priority
        self.sieves.sort(key=lambda x: x.priority)

    async def launch_hooks_by_event(self, event_type):
        """
        Launch all hooks that belong to an event type
        """
        to_run = []

        # On ready hooks
        if event_type == EventType.on_ready:
            to_run = self.run_on_ready

        # Timer events
        elif event_type == EventType.timer_event:
            # Gather only expired events
            # TODO put these in a queue to make it more efficient
            now = tutils.tnow()
            for plugin in self.plugins.values():
                for hook in plugin.periodic:
                    # If it expired, add it to the queue
                    if now - hook.last_time > hook.interval:
                        to_run.append(hook)
                        hook.last_time = now

        for hook in to_run:
            for server in self._servers:
                await self.launch_server_event(hook, server, event_type)

    async def execute_hook(self, hook, args):
        """
        Runs the hook

        Returns the hook result
        """

        result = None
        # If async plugin, await its result
        if asyncio.iscoroutinefunction(hook.function):
            result = await hook.function(**args)
        else:
            result = hook.function(**args)

        return result

    def _prepare_parameters(self, hook, args):
        #
        required = set(hook.required_args)
        given = set(args.keys())

        # Save the difference between required and given args
        diff = required - given
        if diff:
            raise ValueError(
                f"Args required by {hook.name} not found: {list(diff)}")

        actual_args = {}
        for arg in required:
            actual_args[arg] = args[arg]

        return actual_args

    async def launch_command(self, hook, event, event_text):
        if not event.server_id:
            # It's a PM
            return

        # Check if the command should run in the triggered server
        # TODO save commands per server
        if not hook.has_server_id(str(event.server_id)):
            return

        # Prepare the args for the function call
        # TODO export this to a visible structure
        args = {}
        args["bot"] = self.bot
        args["event"] = event
        args["text"] = event_text
        args["reply"] = event.reply
        args["reply_embed"] = event.reply_embed

        # Add storage if needed
        if hook.needs_storage:
            # Get sever data
            srv_data = self.get_server_data(event.server_id)

            # Fill in extra parameters
            args["storage"] = srv_data.get_plugin_storage(hook.plugin.name)
            args["storage_loc"] = srv_data.get_data_location(hook.plugin.name)

        # Get proper args
        parsed_args = self._prepare_parameters(hook, args)

        # Run the plugin and return the result
        ret_value = await self.execute_hook(hook, parsed_args)

        # By default, reply() with the result
        if ret_value:
            event.reply(str(ret_value))

    async def launch_server_event(self, hook, server, event_type):
        """
        Launch an event triggered on a server
        """
        # Prepare the args for the function call
        # TODO export this to a visible structure
        args = {}
        args["bot"] = self.bot
        args["server"] = server
        args["send_message"] = self.bot.client.send_message

        # Add storage if needed
        if hook.needs_storage:
            # Get sever data
            srv_data = self.get_server_data(server.id)

            # Fill in extra parameters
            args["storage"] = srv_data.get_plugin_storage(hook.plugin.name)
            args["storage_loc"] = srv_data.get_data_location(hook.plugin.name)

        # Get proper args
        parsed_args = self._prepare_parameters(hook, args)

        # Run the plugin and return the result
        return await self.execute_hook(hook, parsed_args)

    async def launch_event(self, hook, event_type):
        """
        Launch a event that does not belong to a server
        """
        # Prepare the args for the function call
        # TODO export this to a visible structure
        args = {}
        args["bot"] = self.bot
        args["send_message"] = self.bot.client.send_message

        # Get proper args
        parsed_args = self._prepare_parameters(hook, args)

        # Run the plugin and return the result
        return await self.execute_hook(hook, parsed_args)

    def unload_plugin(self, path):
        """
        Unloads the plugin from the given path, unregistering all hooks
        from the plugin.

        Returns True if the plugin was unloaded, False if the plugin wasn't
        loaded in the first place.

        :type path: str
        :rtype: bool
        """

        # make sure this plugin is actually loaded
        if path not in self.plugins:
            return False

        # get the loaded plugin
        plugin = self.plugins[path]

        # unregister commands
        for command_hook in plugin.commands:
            if command_hook.name in self.commands:
                del self.commands[command_hook.name]

        # unregister raw hooks
        for raw_hook in plugin.raw_hooks:
            if raw_hook.is_catch_all():
                self.catch_all_triggers.remove(raw_hook)
            else:
                for trigger in raw_hook.triggers:
                    # this can't be not true
                    assert trigger in self.raw_triggers

                    self.raw_triggers[trigger].remove(raw_hook)
                    # if that was the last hook for this trigger
                    if not self.raw_triggers[trigger]:
                        del self.raw_triggers[trigger]

        # unregister events
        for event_hook in plugin.events:
            for event_type in event_hook.types:
                # this can't be not true
                assert event_type in self.event_type_hooks

                self.event_type_hooks[event_type].remove(event_hook)
                # if that was the last hook for this event type
                if not self.event_type_hooks[event_type]:
                    del self.event_type_hooks[event_type]

        # unregister regexps
        for regex_hook in plugin.regexes:
            for regex_match in regex_hook.regexes:
                self.regex_hooks.remove((regex_match, regex_hook))

        # unregister sieves
        for sieve_hook in plugin.sieves:
            self.sieves.remove(sieve_hook)

        # remove last reference to plugin
        del self.plugins[plugin.name]

        logger.info("Unloaded all plugins from {}.py".format(plugin.name))

        return True

    def load_plugin(self, fname):
        """
        Load a whole plugin file
        """

        # Try unloading the file first
        self.unload_plugin(fname)
        plugin = self._load_plugin(fname)

        if plugin:
            self.plugins[fname] = Plugin(fname, plugin)
            asyncio.run_coroutine_threadsafe(
                self.finalize_plugin(self.plugins[fname]),
                self.bot.loop)

    def _load_plugin(self, fname):
        """
        Load a plugin and return the importlib result
        """
        logger.debug("Loading %s" % fname)

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

            logger.debug("Error loading %s:\n\t%s" % (fname, e))
            traceback.print_exc()
            return None


class Plugin:
    """
    Hold data about a plugin file
    """

    def __init__(self, name, module):
        self.name = name

        (
            self.commands,
            self.regexes,
            self.raw_hooks,
            self.sieves,
            self.events,
            self.periodic,
            self.run_on_start,
            self.run_on_ready,
        ) = find_hooks(self, module)
