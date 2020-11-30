# -*- coding: utf-8 -*-
import re
import random
import plugins.paged_content as paged
import utils.discord_utils as dutils
from SpankyWorker import hook
from core.event import EventType
from hook.permissions import Permission


@hook.command(format="user")
async def grab(text, channel, storage, reply, event):
    """<user> - grab user's last message"""

    to_grab = None

    # Check if we're grabbing a user
    user_id = dutils.str_to_id(text)
    if event.author.id == user_id:
        reply("Didn't your mom teach you not to grab yourself in public?")
        return

    messages = await channel.async_get_latest_messages(100)

    to_grab = None
    for msg in messages:
        if msg.author.id == user_id:
            to_grab = msg
            break

    # Or we may be grabbing a message link or ID
    if not to_grab:
        _, _, msg_id = dutils.parse_message_link(text)

        if not msg_id:
            msg_id = text
        try:
            to_grab = await channel.async_get_message(msg_id)
        except:
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


def get_all_data(func, storage):
    content = []

    for msg in storage["grabs"]:
        if func == None or func(msg):
            content.append(msg)

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
        content = get_data(lambda m: text == m["id"], storage)

    if len(content) == 0:
        await async_send_message("Nothing found.")
        return
    else:
        paged_content = paged.element(
            content, async_send_message, "Grabs containing %s" % text)
        await paged_content.get_crt_page()


@hook.command(permissions=Permission.admin)
def del_grab(text, storage):
    """
    Delete a grab entry. Specify what the grab message contains or the message ID
    """

    to_delete = get_all_data(lambda m: text in m["text"], storage)

    if len(to_delete) > 1:
        msg = "Found more than one results (%d). Not deleting." % len(
            to_delete)

        if len(to_delete) < 10:
            msg += "\nThe IDs are: "
            msg += " ".join(i["id"] for i in to_delete)

        return msg
    elif len(to_delete) == 1:
        storage["grabs"].remove(to_delete[0])
        storage.sync()
        return "Deleted %s" % to_delete[0]["id"]
    else:
        to_delete_by_id = get_all_data(lambda m: text == m["id"], storage)
        if len(to_delete_by_id) == 1:
            storage["grabs"].remove(to_delete_by_id[0])
            storage.sync()
            return "Deleted %s" % text
