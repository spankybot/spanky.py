import enum
import os

from utils import storage

class ServerData():
    """
    Holds information about a server
    """
    def __init__(self, server):
        self.meta = storage.dsdict(server.id, "meta.json")
        self.server = server
        self.server_id = str(server.id)

        self.stor_cache = {}

        self.meta["name"] = server.name
        self.meta["id"] = server.id

    def get_plugin_storage_raw(self, stor_file):
        """
        Get the location of the plugin storage json file
        """
        if self.server_id + stor_file not in self.stor_cache:
            self.stor_cache[self.server_id + stor_file] = \
                storage.dsdict(self.server_id, stor_file)

        return self.stor_cache[self.server_id + stor_file]

    def get_plugin_storage(self, plugin_fname):
        """
        Get the location of the plugin storage json file but with nicer interface
        """
        # Replace paths
        stor_file = plugin_fname.replace(".py", "").replace(os.sep, "_")

        return self.get_plugin_storage_raw(f"{stor_file}.json")

    def get_data_location(self, plugin_fname):
        return os.path.join(storage.DS_LOC, self.server_id, plugin_fname, "_data/")