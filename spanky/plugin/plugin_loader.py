import glob
import os
import importlib
import logging

from spanky.plugin.hook_logic import find_hooks, find_tables

logger = logging.getLogger('spanky')

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

class PluginLoader():
    def __init__(self, path_list):
        self.modules = []
        self.plugins = {}
        
        # Load each path
        for path in path_list:
            self.plugins.update(self.load_plugins(path))

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
        
    def load_plugins(self, path):
        """
        Load plugins from a specified path.
        """
        plugins = glob.iglob(os.path.join(path, '*.py'))
        plugin_dict = {}
        for file in plugins:
            plugin_data = self.load_plugin(file)
            
            if plugin_data:
                plugin_dict[file] = Plugin(file, plugin_data)

        return plugin_dict