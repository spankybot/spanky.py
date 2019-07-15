import enum
from spanky.utils import storage

@enum.unique
class Permission(enum.Enum):
    admin     = 0   # Can be used by anyone with admin rights in a server
    bot_owner = 99  # Bot big boss

class PermissionMgr():
    def __init__(self, server):
        self.meta = storage.dsdict(server.id, "meta.json")
        self.server = server

        self.stor_cache = {}

        if "name" not in self.meta.keys():
            self.meta["name"] = server.name

        if "id" not in self.meta.keys():
            self.meta["id"] = server.id

    def get_plugin_storage(self, stor_file):
        if self.server.id + stor_file not in self.stor_cache:
            self.stor_cache[self.server.id + stor_file] = storage.dsdict(self.server.id, stor_file)

        return self.stor_cache[self.server.id + stor_file]

    def get_data_location(self, name):
        return storage.DS_LOC + "/" + str(self.server.id) + "/" + name + "_data/"
