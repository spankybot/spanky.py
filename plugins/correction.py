#-*- coding: utf-8 -*-
from spanky.plugin import hook

MAX_LEN = 50

@hook.command(format="word replacement")
async def s(text, channel, reply, event, bot):
    """<word replacement> - replace 'word' with replacement"""
    text = text.split()

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

