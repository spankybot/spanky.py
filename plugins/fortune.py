import asyncio
import codecs
import os
import random

from spanky.plugin import hook


@hook.on_start()
def load_fortunes():
    path = os.path.join("plugin_data/fortunes.txt")
    global fortunes
    with codecs.open(path, encoding="utf-8") as f:
        fortunes = [line.strip() for line in f.readlines() if not line.startswith("//")]


@asyncio.coroutine
@hook.command(autohelp=False)
def fortune():
    """- hands out a fortune cookie"""
    return random.choice(fortunes)
