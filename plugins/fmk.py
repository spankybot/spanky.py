import codecs
import os
import random

from spanky.plugin import hook

@hook.on_start()
def load_fmk():
    """
    :type bot: cloudbot.bot.Cloudbot
    """
    global fmklist

    with codecs.open(os.path.join("plugin_data/fmk.txt"), encoding="utf-8") as f:
        fmklist = [line.strip() for line in f.readlines() if not line.startswith("//")]


@hook.command("fmk", autohelp=False)
def fmk(text):
    """[nick] - Fuck, Marry, Kill"""
    return " {} FMK - {}, {}, {}".format((text.strip() if text.strip() else ""), random.choice(fmklist),
                                          random.choice(fmklist), random.choice(fmklist))
