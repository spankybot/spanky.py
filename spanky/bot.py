import glob
import os
import importlib
import logging
import json
import asyncio

from spanky.hook_logic import find_hooks, find_tables
from spanky.database.db import db_data
from spanky.event import Event

logger = logging.getLogger('spanky')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

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
        :type bot: cloudbot.bot.CloudBot
        """
        if self.tables:
            # if there are any tables
            logger.info("Unregistering tables for {}".format(self.title))

            for table in self.tables:
                db_data.db_metadata.remove(table)

class PluginManager():
    def __init__(self, path_list):
        self.modules = []
        self.plugins = {}
        
        with open('bot_config.json') as data_file:
            self.config = json.load(data_file)

        self.loop = asyncio.get_event_loop()

        db_path = self.config.get('database', 'sqlite:///cloudbot.db')
        
        # Open the database first
        self.db = db_data(db_path)
        
        # Load each path
        for path in path_list:
            self.load_plugins(path)

    def load_plugin(self, fname):
        """
        Load a whole plugin file
        :param fname: file name to load
        """

        # Try unloading the file first
        self.unload_plugin(fname)
        return self._load_plugin(fname)

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

    def unload_plugin(self, fname):
        """
        Unload a plugin.
        """
        pass

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
        
    def load_plugins(self, path):
        """
        Load plugins from a specified path.
        """
        plugins = glob.iglob(os.path.join(path, '*.py'))
        for file in plugins:
            plugin_data = self.load_plugin(file)
            
            if plugin_data:
                self.plugins[file] = Plugin(file, plugin_data)

        for path, plugin in self.plugins.items():
            self.finalize_plugin(plugin)

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