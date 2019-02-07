#-*- coding: utf-8 -*-
import re
import random
from spanky.plugin import hook
from spanky.plugin.event import EventType

MAX_LEN = 10

@hook.command(format="word replacement")
async def s(text, channel, reply, event, bot):
    """<word replacement> - replace 'word' with replacement"""
    text = text.split()

    messages = await channel.async_get_latest_messages(MAX_LEN)

    for msg in messages:
        if msg.id == event.msg.id or msg.author.id == bot.get_own_id() or msg.text.startswith(".s"):
            continue
        if text[0] in msg.text:
            msg = "<%s> %s" % (msg.author.name, msg.text.replace(text[0], text[1]))
            reply(msg)
            return

