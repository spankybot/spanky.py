import logging
import json
import asyncio

from spanky.plugin.event import Event
from spanky.database.db import db_data
from spanky.plugin.plugin_loader import PluginLoader

logger = logging.getLogger('spanky')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


class PluginManager():
    def __init__(self, path_list):
        self.plugins = {}
        self.commands = {}
        self.event_type_hooks = {}
        self.regex_hooks = []
        self.sieves = []
        
        with open('bot_config.json') as data_file:
            self.config = json.load(data_file)

        self.loop = asyncio.get_event_loop()

        db_path = self.config.get('database', 'sqlite:///cloudbot.db')
        
        # Open the database first
        self.db = db_data(db_path)
        
        loader = PluginLoader(path_list)
        self.plugins = loader.plugins
        
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
            
    
    def _prepare_parameters(self, hook, event):
        """
        Prepares arguments for the given hook

        :type hook: cloudbot.plugin.Hook
        :type event: cloudbot.event.Event
        :rtype: list
        """
        
        parameters = []
        for required_arg in hook.required_args:
            if hasattr(event, required_arg):
                value = getattr(event, required_arg)
                parameters.append(value)
            else:
                logger.error("Plugin {} asked for invalid argument '{}', cancelling execution!"
                             .format(hook.description, required_arg))
                logger.debug("Valid arguments are: {} ({})".format(dir(event), event))
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

        :type event: cloudbot.event.Event | cloudbot.event.CommandEvent
        :rtype: bool
        """
        # Run the plugin with the message, and wait for it to finish
        return self._execute_hook(event.hook, event)