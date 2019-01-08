import codecs
import os
import random

from spanky.plugin import hook


@hook.on_start()
def load_kenm():
    """
    :type bot: cloudbot.bot.Cloudbot
    """
    global kenm

    with codecs.open(os.path.join("plugin_data/kenm.txt"), encoding="utf-8") as f:
        kenm = [line.strip() for line in f.readlines() if not line.startswith("//")]


@hook.command("kenm", autohelp=False)
def kenm():
    """- Wisdom from Ken M."""
    return random.choice(kenm)
