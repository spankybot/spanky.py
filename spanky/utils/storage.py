import os
import json
import collections

DS_LOC = "storage_data/"

class dstype():
    def __init__(self, parent, name):
        
        os.system("mkdir -p %s" % DS_LOC + "/" + parent + "/backup")
        
        location = parent + "/" + name
        
        data_obj = self.get_obj(location)
        if data_obj:
            self.data = data_obj

        self.location = location
        self.backup_name = parent + "/backup/" + name
        
    def do_sync(self, obj, name, backup_name):
        
        try:
            # Check if the current file is valid
            json.load(open(DS_LOC + name, "r"))
            # If yes, do a backup
            os.system("cp %s %s" % (DS_LOC + name, DS_LOC + backup_name))
        except:
            print("File at %s is not valid" % (DS_LOC + name))
            
        file = open(DS_LOC + name, "w")
        json.dump(obj, file, indent=4, sort_keys=True)
        
    def sync(self):
        self.do_sync(self.data, self.location, self.backup_name)
    
    def get_obj(self, location):
        try:
            data = json.load(open(DS_LOC + location, "r"))
            return data
        except:
            return None
    
class dsdict(dstype, collections.UserDict):
    def __init__(self, parent, name):
        collections.UserDict.__init__(self)
        dstype.__init__(self, parent, name)
        
    def __getitem__(self, key):
        try:
            return collections.UserDict.__getitem__(self, key)
        except:
            return None

    def __setitem__(self, key, value):
        collections.UserDict.__setitem__(self, key, value)
        self.sync()
        return self.data
