import random
import re
from pathlib import Path
from spanky.data2 import res

from spanky.plugin import hook

cheer_re = re.compile(r"\\o/", re.IGNORECASE)

cheers = []


@hook.on_start()
def load_cheers(bot):
    cheers.clear()
    cheers.extend(res.readlines("cheers.txt"))


@hook.command()
def cheer():
    """
    :type chan: str
    """
    shit = random.choice(cheers)
    return shit
