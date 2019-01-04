import enum
from spanky.utils import storage

@enum.unique
class Permission(enum.Enum):
    admin    = 0
    
class PermissionMgr():
    def __init__(self, server):
        self.admin = storage.dsdict(server.id, "admin.json")
        self.meta = storage.dsdict(server.id, "meta.json")
        self.cmds = storage.dsdict(server.id, "commands.json")
        self.config = storage.dsdict(server.id, "config.json")
        self.server = server
        
        self.stor_cache = {}
        
        if "default_bot_chan" not in self.config.keys():
            self.config["default_bot_chan"] = ''
        
        if "name" not in self.meta.keys():
            self.meta["name"] = server.name
            
        if "id" not in self.meta.keys():
            self.meta["id"] = server.id
        
    def set_admin(self, admin):
        self.admin["admin_id"] = admin
        return None
    
    def get_admin(self):
        if "admin_id" in self.admin.keys():
            return self.admin["admin_id"]
        
        return None
    
    def add_role_to_cmd(self, role_id, cmd):
        if role_id not in self.server.get_role_ids():
            return "Invalid role"
        
        return None
    
    def get_plugin_storage(self, stor_file):
        if stor_file not in self.stor_cache:
            self.stor_cache[self.server.id + stor_file] = storage.dsdict(self.server.id, stor_file)

        return self.stor_cache[self.server.id + stor_file]
