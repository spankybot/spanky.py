import asyncio
import codecs
import os
import random

from spanky.plugin import hook


@hook.on_start()
def load_responses():
    path = os.path.join("plugin_data/8ball_responses.txt")
    global responses
    with codecs.open(path, encoding="utf-8") as f:
        responses = [line.strip() for line in
                     f.readlines() if not line.startswith("//")]


@asyncio.coroutine
@hook.command("8ball")
def eightball():
    """<question> - asks the all knowing magic electronic eight ball <question>"""
    magic = random.choice(responses)
    message = "shakes the magic 8 ball... {}".format(magic)

    return message
