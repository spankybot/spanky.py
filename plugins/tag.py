# -*- coding: utf-8 -*-
from spanky.plugin import hook
from spanky.plugin.permissions import Permission
from spanky.hook2.event import EventType
import requests
import os
import re
import random
import string
import nextcord

LARROW = u"⬅"
RARROW = u"➡"
MAX_LEN = 500


def save_picture(url, tag_name, message, storage, storage_loc):
    if tag_name in storage.keys():
        message("%s already exists!" % tag_name)
        return

    name = "".join(
        random.choice(string.ascii_letters + string.digits) for i in range(10)
    )
    ext = url.split(".")[-1]

    try:
        fname = name + "." + ext
        os.system("mkdir -p %s" % storage_loc)
        f = open(storage_loc + fname, "wb")
        f.write(requests.get(url).content)
        f.close()

        storage[tag_name] = {}
        storage[tag_name]["type"] = "picture"
        storage[tag_name]["location"] = fname

        storage.sync()

        message("Added picture tag")
    except:
        del storage[tag_name]
        import traceback

        traceback.print_exc()


def save_text(text, tag_name, message, storage):
    if tag_name in storage.keys():
        message("already exists")
        return

    os.makedirs("tags", exist_ok=True)

    try:
        storage[tag_name] = {}
        storage[tag_name]["type"] = "text"
        storage[tag_name]["content"] = text
        storage.sync()

        message("Added text tag")
    except:
        del storage[tag_name]
        storage.sync()

        import traceback

        traceback.print_exc()


def get_page_for(content, page_len):
    pages = [""]
    crt_page = 0
    crt_page_len = 0
    try:
        for idx, i in enumerate(content):
            crt_page_len += len(i)
            pages[crt_page] += "`%s`" % i

            if crt_page_len >= page_len:
                crt_page += 1
                crt_page_len = 0
                pages.append("")
            elif idx < len(content) - 1:
                pages[crt_page] += ", "

        return pages
    except Exception as e:
        print(str(e))


@hook.event(EventType.reaction_add)
async def do_page(bot, event, storage, send_message):
    if event.msg.author.id != bot.get_own_id():
        return

    if (
        event.reaction.emoji.name == LARROW or event.reaction.emoji.name == RARROW
    ) and event.msg.text.startswith("Tags"):
        crt_page = int(re.search(r"Tags (.*?)/", event.msg.text).group(1))
        tot_pages = int(re.search(r"/(.*?):", event.msg.text).group(1))

        if event.reaction.emoji.name == RARROW and crt_page + 1 <= tot_pages:
            crt_page += 1
        elif event.reaction.emoji.name == LARROW and crt_page > 1:
            crt_page -= 1
        else:
            await event.msg.async_remove_reaction(
                event.reaction.emoji.name, event.author
            )
            return

        await event.msg.async_remove_reaction(event.reaction.emoji.name, event.author)

        content = get_page_for(sorted(list(storage)), MAX_LEN)
        send_message(
            "Tags %d/%d: %s" % (crt_page, tot_pages, content[crt_page - 1]),
            event.channel.id,
        )


@hook.command()
async def tag(text, send_file, storage, storage_loc, async_send_message):
    """
    <tag> - Return a tag. '.tag list' lists tags, '.tag random' returns random tag
    """
    text = text.split()
    if len(text) == 0:
        return __doc__

    tag = text[0]

    if tag == "list":
        content = get_page_for(sorted(list(storage)), MAX_LEN)
        if len(content) > 1:
            message = await async_send_message(
                "Tags 1/%d: %s" % (len(content), content[0])
            )
            await message.async_add_reaction(LARROW)
            await message.async_add_reaction(RARROW)
        else:
            await async_send_message("Tags: %s" % content[0])
    else:
        msg = ""
        if tag == "random":
            tag = random.choice(list(storage.keys()))
            msg = "(%s)\n" % tag

        if tag in storage:
            if storage[tag]["type"] == "text":

                content = storage[tag]["content"]
                await async_send_message(
                    msg + content, allowed_mentions=nextcord.AllowedMentions.none()
                )
            elif storage[tag]["type"] == "picture":
                send_file(storage_loc + storage[tag]["location"])
        else:
            await async_send_message("Syntax is: `.tag list` or `.tag <name>`")


@hook.command()
def tag_add(text, event, reply, storage, storage_loc):
    """
    <identifier content> - add tag content as indentifier
    """
    text = text.split(maxsplit=1)
    for att in event.attachments:
        if len(text) != 1:
            return "Format is: `.tag_add <name> picture`"

        save_picture(att.url, text[0], reply, storage, storage_loc)
        return
    else:
        if len(text) < 2:
            return "If no picture is attached, add more words"

        save_text(text[1], text[0], reply, storage)


@hook.command(permissions=Permission.admin, format="cmd")
def tag_del(text, storage, storage_loc):
    """
    <tag> - delete a tag
    """
    if text not in storage.keys():
        return "%s is not a tag" % text

    if storage[text]["type"] == "picture":
        os.remove(storage_loc + storage[text]["location"])

    del storage[text]
    storage.sync()
    return "Done!"
