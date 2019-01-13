#-*- coding: utf-8 -*-
import re
import random
from spanky.plugin import hook
from spanky.plugin.event import EventType

MAX_LEN = 500
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
            print(e)

    if not to_grab:
        reply("Couldn't find anything.")

    if not storage["grabs"]:
        storage["grabs"] = []

    grab_data = {}
    grab_data["text"] = to_grab.clean_content
    grab_data["id"] = to_grab.id
    grab_data["author_id"] = to_grab.author.id
    grab_data["author_name"] = to_grab.author.name

    storage["grabs"].append(grab_data)
    storage.sync()

    reply("Done.")

def get_page_for(content, page, page_len, total_pages):
    pages = [""] * total_pages
    crt_page = 0
    crt_page_len = 0
    try:
        for i in content:
            crt_page_len += len(i)
            pages[crt_page] += "`%s`" % i

            if crt_page_len >= page_len:
                crt_page += 1
                crt_page_len = 0
            else:
                pages[crt_page] += ", "

        return pages[page]
    except Exception as e:
        print(str(e))

@hook.event(EventType.reaction_add)
async def do_page(bot, event, storage, send_message):
    if event.msg.author.id != bot.get_own_id():
        return

    if (event.reaction.emoji.name == LARROW or \
        event.reaction.emoji.name == RARROW) and \
        event.msg.text.startswith("Grab"):

        text = event.msg.text.split("\n")[0]
        is_content = True

        old_page = -99
        if text.startswith("Grabs"):
            old_page = int(re.search(r'Grabs page (.*?)/', text).group(1))
        elif text.startswith("Grabl"):
            is_content = False
            old_page = int(re.search(r'Grabl page (.*?)/', text).group(1))

        tot_pages = int(re.search(r'/(.*?):', text).group(1))
        search_term = re.search(r': (.*)', text).group(1)

        crt_page = old_page
        if event.reaction.emoji.name == RARROW and old_page + 1 <= tot_pages:
            crt_page = old_page + 1
        elif event.reaction.emoji.name == LARROW and old_page > 1:
            crt_page = old_page - 1

        await event.msg.async_remove_reaction(event.reaction.emoji.name, event.author)

        if crt_page == old_page:
            return

        if is_content:
            content, total_len = get_content_for(search_term, storage)
            msg = "Grabs"
        else:
            content, total_len = get_content_by(search_term, storage)
            msg = "Grabl"

        msg += " page %d/%d: %s\n" % (crt_page, tot_pages, search_term)
        msg += get_page_for(content, crt_page - 1, MAX_LEN, total_len // MAX_LEN)

        send_message(msg, event.channel.id)

def get_content_for(term, storage):
    total_len = 0
    content = []
    for msg in storage["grabs"]:
        if term in msg["text"]:
            to_add = "`<%s> %s`" % (msg["author_name"], msg["text"])
            total_len += len(to_add)
            content.append(to_add)

    return content, total_len


def get_content_by(term, storage):
    total_len = 0
    content = []
    for msg in storage["grabs"]:
        if term == msg["author_id"]:
            to_add = "`<%s> %s`" % (msg["author_name"], msg["text"])
            total_len += len(to_add)
            content.append(to_add)

    return content, total_len

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

@hook.command(format="word")
async def grabl(event, storage, async_send_message, str_to_id, text):
    """
    <user> - List quotes for user.
    """
    text = str_to_id(text)
    content, total_len = get_content_by(text, storage)

    total_pages = 0
    if total_len > MAX_LEN:
        total_pages = total_len // MAX_LEN

    if len(content) == 0:
        await async_send_message("Nothing found.")
        return
    else:
        if total_pages > 0:
            msg = "Grabl page 1/%d: %s\n" % (total_pages, text)
            msg += get_page_for(content, 0, MAX_LEN, total_pages)

            message = await async_send_message(msg)

            # Add arrow emojis
            await message.async_add_reaction(LARROW)
            await message.async_add_reaction(RARROW)
        else:
            msg = "Grab search for user: %s\n" % (text)
            msg += ", ".join(i for i in content)

            message = await async_send_message(msg)

@hook.command(format="word")
async def grabs(event, storage, async_send_message):
    """
    <expression> - Search for 'expression' in grab texts.
    """
    text = event.msg.clean_content.split(" ", maxsplit=1)[1]
    content, total_len = get_content_for(text, storage)

    total_pages = 0
    if total_len > MAX_LEN:
        total_pages = total_len // MAX_LEN

    if len(content) == 0:
        await async_send_message("Nothing found.")
        return
    else:
        if total_pages > 0:
            msg = "Grabs page 1/%d: %s\n" % (total_pages, text)
            msg += get_page_for(content, 0, MAX_LEN, total_pages)

            message = await async_send_message(msg)

            # Add arrow emojis
            await message.async_add_reaction(LARROW)
            await message.async_add_reaction(RARROW)
        else:
            msg = "Grab search for: %s\n" % (text)
            msg += ", ".join(i for i in content)

            message = await async_send_message(msg)

