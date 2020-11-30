"""
Provide storage backed dicts
"""
import pathlib
import json
import collections
from shutil import copyfile
from .log import botlog

DS_LOC = "storage_data/"
logger = botlog("storage.log")

### TODO check validity of backup before using it


class dstype:
    def __init__(self, parent, name):
        parent = str(parent)
        logger.debug(f"Initializing {parent}/{name}")

        # Compute main and backup locations
        self.location = pathlib.PurePath(DS_LOC, parent, name)
        self.backup_name = pathlib.PurePath(DS_LOC, parent, "backup", name)

        # Create backup location
        pathlib.Path(self.backup_name.parent).mkdir(
            parents=True, exist_ok=True)

        data_obj = self.get_obj(self.location)
        if data_obj:
            self.data = data_obj

    def do_sync(self, obj, name, backup_name):
        try:
            logger.debug(f"Do sync on {name}")

            # Check if the current file is valid
            json.load(open(name, "r"))

            # If yes, do a backup
            copyfile(name, backup_name)

            logger.debug("Load/sync OK")
        except Exception as e:
            print(e)
            print("File at %s is not valid" % (name))
            logger.debug("Sync error - file invalid")

        logger.debug("Open file")
        file = open(name, "w")

        json.dump(obj, file, indent=4, sort_keys=True)
        logger.debug("Sync finished")

    def sync(self):
        self.do_sync(self.data, self.location, self.backup_name)

    def get_obj(self, location):
        try:
            logger.info("Load file %s" % location)
            data = json.load(open(location, "r"))
            return data
        except: # TODO handle with json error
            logger.error("Trying backup %s" % location)
            try:
                # Try the backup
                data = json.load(open(self.backup_name, "r"))

                logger.critical(f"Loaded backup for {self.location}")
                return data
            except: # TODO handle it
                logger.error(f"Could not load {self.location}")
                return None


class dsdict(dstype, collections.UserDict):
    """
    Dict that performs all reads/writes from disk
    """
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
