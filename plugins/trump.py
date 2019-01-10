import codecs
import json
import os
import random
import asyncio

from spanky.plugin import hook
from spanky.utils import textgen

@hook.on_start()
def load_trumps():
    """
    :type bot: cloudbot.bot.CloudBot
    """
    global trump_data

    with codecs.open(os.path.join("plugin_data/trump.json"), encoding="utf-8") as f:
        trump_data = json.load(f)

@asyncio.coroutine
@hook.command(format="user")
def trump(text, send_message):
    """trump a user."""
    user = text.strip()
    generator = textgen.TextGenerator(trump_data["templates"], trump_data["parts"], variables={"user": user})
    send_message(generator.generate_string())
