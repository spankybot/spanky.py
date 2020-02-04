#-*- coding: utf-8 -*-
from spanky.plugin import hook
import re2

MAX_LEN = 50

@hook.command()
async def s(text, channel, reply, event, bot):
    """<word replacement> - replace 'word' with replacement"""
    text = text.split()
    if len(text) == 0 or len(text) > 2:
        msg = "Invalid format"
        msg += ": " + "\n`" + "<word replacement> - replace 'word' with replacement`"
        msg += "\n`" + "if only one word is specified, it will be replaced with a blankspace`"
        reply(msg, timeout=15)
        return

    if len(text) == 1:
        text.append("")

    messages = await channel.async_get_latest_messages(MAX_LEN)

    for msg in messages:
        if msg.id == event.msg.id or msg.author.id == bot.get_own_id() or msg.text.startswith(".s"):
            continue
        if text[0] in msg.text:
            text_array = msg.text.split(" ")

            for index, word in enumerate(text_array):
                l_arrow = word.find("<")
                r_arrow = word.find(">")

                if (l_arrow < 0 and r_arrow < 0) or (l_arrow > r_arrow):
                    text_array[index] = word.replace(text[0], text[1])

            msg = "<%s> %s" % (msg.author.name, " ".join(text_array))
            reply(msg)
            return

@hook.command()
async def ss(text, channel, reply, event, bot):
    """<regex replacement> - replace regex with replacement"""

    text = text.split()
    if len(text) == 0 or len(text) > 2:
        msg = "Invalid format"
        msg += ": " + "\n`" + "<regex replacement> - replace regex with replacement`"
        msg += "\n`" + "if only the regex is specified, it will be replaced with a blankspace`"
        reply(msg, timeout=15)
        return

    if len(text) == 1:
        text.append("")

    messages = await channel.async_get_latest_messages(MAX_LEN)

    try:
        regex = re2.compile(text[0]) 
    except Exception as e:
        reply("You don't have a valid regex")
        return

    for msg in messages:
        if msg.id == event.msg.id or msg.author.id == bot.get_own_id() or msg.text.startswith(".s"):
            continue
        if regex.search(msg.text) != None:
            msg = "<%s> %s" % (msg.author.name, regex.sub(text[1], msg.text))
            reply(msg)
            return