#-*- coding: utf-8 -*-
import re
import random
import plugins.paged_content as paged
from spanky.plugin import hook
from spanky.plugin.event import EventType

MAX_LEN = 10
LARROW=u'⬅'
RARROW=u'➡'

@hook.command(format="user")
async def grab(text, channel, str_to_id, storage, reply, event):
    """<user> - grab user's last message"""
    if not text.startswith("https://discordapp.com/channels/"):
        user_id = str_to_id(text)

        if event.author.id == user_id:
            reply("Didn't your mom teach you not to grab yourself in public?")
            return

        messages = await channel.async_get_latest_messages(100)

        to_grab = None
        for msg in messages:
            if msg.author.id == user_id:
                to_grab = msg
                break
    else:
        try:
            to_grab = await channel.async_get_message(text.split("/")[-1])
        except Exception as e:
            import traceback
            traceback.print_exc()

    if not to_grab:
        reply("Couldn't find anything.")

    if not storage["grabs"]:
        storage["grabs"] = []

    for elem in storage["grabs"]:
        if elem["id"] == to_grab.id:
            reply("Message already grabbed")
            return

    grab_data = {}
    grab_data["text"] = to_grab.clean_content
    grab_data["id"] = to_grab.id
    grab_data["author_id"] = to_grab.author.id
    grab_data["author_name"] = to_grab.author.name

    storage["grabs"].append(grab_data)
    storage.sync()

    reply("Done.")

def get_data(func, storage):
    content = []

    for msg in storage["grabs"]:
        if func == None or func(msg):
            content.append("<%s> %s" % (msg["author_name"], msg["text"]))

    return content

@hook.command()
def grabr(storage):
    """
    Grab random quote
    """
    item = random.choice(storage["grabs"])

    return "<%s> %s" % (item["author_name"], item["text"])

@hook.command(format="word")
def grabu(text, storage, str_to_id):
    """
    <user> - Grab random quote from user
    """

    user = str_to_id(text)
    content = []
    for msg in storage["grabs"]:
        if msg["author_id"] == user:
            content.append(msg["text"])

    if len(content) == 0:
        return "Nothing here."

    return random.choice(content)

@hook.command
async def grabl(event, storage, async_send_message, str_to_id, user_id_to_name, text):
    """
    <user> - List quotes for user. If no user is specified, it lists everything on the server.
    """
    text = str_to_id(text)
    if text != "":
        content = get_data(lambda m: m["author_id"] == text, storage)
        description = "Grabs for %s:" % user_id_to_name(text)
    else:
        content = get_data(None, storage)
        description = "All server grabs:"

    if len(content) == 0:
        await async_send_message("Nothing found.")
        return
    else:
        paged_content = paged.element(content, async_send_message, description)
        await paged_content.get_crt_page()

@hook.command(format="word")
async def grabs(event, storage, async_send_message):
    """
    <expression> - Search for 'expression' in grab texts.
    """
    text = event.msg.clean_content.split(" ", maxsplit=1)[1]
    content = get_data(lambda m: text in m["text"], storage)

    if len(content) == 0:
        await async_send_message("Nothing found.")
        return
    else:
        paged_content = paged.element(content, async_send_message, "Grabs containing %s" % text)
        await paged_content.get_crt_page()
