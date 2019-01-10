import codecs
import json
import os
import random
import asyncio

from spanky.plugin import hook
from spanky.utils import textgen

def is_valid(target):
    """ Checks if a string is a valid IRC nick. """
    if nick_re.match(target):
        return True
    else:
        return False


@hook.on_start()
def load_spanks(bot):
    """
    :type bot: cloudbot.bot.CloudBot
    """
    global spank_data, bdsm_data

    with codecs.open(os.path.join("plugin_data/spank.json"), encoding="utf-8") as f:
        spank_data = json.load(f)

    with codecs.open(os.path.join("plugin_data/bdsm.json"), encoding="utf-8") as f:
        bdsm_data = json.load(f)

@hook.command
def spank(text, send_message):
    """<user> - Spanks a  <user>"""
    user = text.strip()

    generator = textgen.TextGenerator(spank_data["templates"], spank_data["parts"],
                                      variables={"user": user})
    # act out the message
    send_message(generator.generate_string())

@hook.command("bdsm")
def bdsm(text, send_message):
    """Just a little bit of kinky fun."""
    user = text.strip()
    generator = textgen.TextGenerator(bdsm_data["templates"], bdsm_data["parts"], variables={"user": user})
    send_message(generator.generate_string())
