import logging
import os
import enum
from logging import FileHandler


LOGS_FOLDER = "filelogs/"
logs = {}


@enum.unique
class loglevel(enum.Enum):
    INFO = 0
    DEBUG = 1
    ERROR = 2


# Map corresponding logging levels
logmap = {
    loglevel.INFO: logging.INFO,
    loglevel.DEBUG: logging.DEBUG,
    loglevel.ERROR: logging.ERROR}


def botlog(name, console_level=loglevel.INFO, file_level=loglevel.DEBUG):
    """
    Simple wrapper around the logger object
    """
    if name in logs:
        # set given levels if already here?
        return logs[name]

    if console_level not in logmap.keys():
        raise ValueError("Invalid console logging level provided")

    if file_level not in logmap.keys():
        raise ValueError("Invalid file logging level provided")

    logging_console = logmap[console_level]
    logging_file = logmap[file_level]

    # Create logs folder
    os.makedirs(LOGS_FOLDER, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging_console)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)

    fh = FileHandler("%s/%s.log" % (LOGS_FOLDER, name))
    fh.setLevel(logging_file)
    fh.setFormatter(formatter)

    logger.addHandler(ch)
    logger.addHandler(fh)

    logs[name] = logger
    return logger
