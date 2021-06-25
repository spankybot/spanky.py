import os
import json
import collections
import logging
import platform

from pathlib import Path
from shutil import copyfile

logger = logging.getLogger("storage")
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler("storage.log")
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)

DS_LOC = Path("storage_data/")


class dstype():
    def __init__(self, parent, name):
        parent = Path(parent)
        logger.debug("Initializing %s, %s" % (parent, name))
        os.system("mkdir -p %s" % DS_LOC / parent / "backup")

        self.location = parent / name
        self.backup_name = parent / "backup" / name

        data_obj = self.get_obj(self.location)
        if data_obj:
            self.data = data_obj

    def do_sync(self, obj, name, backup_name):
        try:
            logger.debug("Do sync on " + str(name))

            # Check if the current file is valid
            json.load(open(DS_LOC / name, "r"))
            # If yes, do a backup
            os.system("cp %s %s" % (DS_LOC / name, DS_LOC / backup_name))
            logger.debug("Load/sync OK")
        except:
            print("File at %s is not valid" % (DS_LOC / name))
            logger.debug("Sync error - file invalid")

        logger.debug("Open file")
        file = open(DS_LOC / name, "w")

        json.dump(obj, file, indent=4, sort_keys=True)
        logger.debug("Sync finished")

    def sync(self):
        self.do_sync(self.data, self.location, self.backup_name)

    def get_obj(self, location):
        """
        Get an object from disk
        """

        file_loc = DS_LOC / location
        backup_loc = DS_LOC / self.backup_name

        if not Path(file_loc).exists() and not Path(backup_loc).exists():
            return {}

        try:
            logger.info("Load file %s" % location)
            return json.load(open(file_loc, "r"))
        except:
            logger.error("Trying backup %s" % location)
            try:
                # Try the backup
                data = json.load(open(backup_loc, "r"))

                logger.critical("Loaded backup for " + self.location)
                return data
            except:
                logger.error("Could not load " + self.location)
                return None

class dsdict(dstype, collections.UserDict):
    def __init__(self, parent, name):
        collections.UserDict.__init__(self)
        dstype.__init__(self, parent, name)

    def __getitem__(self, key):
        return self.data.get(key, None)

    def __setitem__(self, key, value):
        collections.UserDict.__setitem__(self, key, value)
        self.sync()
        return self.data
