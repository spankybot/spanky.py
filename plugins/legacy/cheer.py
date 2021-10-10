import random
import re
from pathlib import Path

from spanky.plugin import hook

cheer_re = re.compile(r"\\o/", re.IGNORECASE)

cheers = []


@hook.on_start()
def load_cheers(bot):
    cheers.clear()
    data_file = Path("plugin_data/cheers.txt")
    with data_file.open(encoding="utf-8") as f:
        cheers.extend(line.strip() for line in f if not line.startswith("//"))


@hook.command()
def cheer():
    """
    :type chan: str
    """
    shit = random.choice(cheers)
    return shit
