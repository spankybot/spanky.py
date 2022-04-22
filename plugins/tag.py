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

import plugins.paged_content as paged

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from spanky.hook2.storage import dsdict

LARROW = "⬅"
RARROW = "➡"
MAX_LEN = 500


class Tag:
    def __init__(
        self, name: str, ttype: str, location: Optional[str], content: str, storage
    ):
        self.name = name
        self.storage: dsdict = storage
        self.entry = storage[self.name]
        self.type: str = ttype
        self.location: Optional[str] = None
        self.content: str = ""
        if self.type == "picture":
            self.location = location
        else:
            self.content = content

    def save(self):
        self.storage[self.name] = {}
        self.storage[self.name]["type"] = self.type
        if self.storage[self.name]["type"] == "picture":
            self.storage[self.name]["location"] = self.location
        else:
            self.storage[self.name]["location"] = self.content
        self.storage.sync()

    def delete(self):
        del self.storage[self.name]

    @staticmethod
    def deserialize(name: str, storage):
        if name not in storage:
            return None
        ttype = storage[name]["type"]
        loc = None
        content = ""
        if ttype == "picture":
            loc = storage[name]["location"]
        else:
            content = storage[name]["content"]
        return Tag(name, ttype, loc, content, storage)

    # Always wrap create_picture and create_text in a try-except structure!

    @staticmethod
    def create_picture(tag_name: str, url: str, storage, storage_loc: str):
        if tag_name in storage:
            raise NameError(f"Tag with name {repr(tag_name)} already exists!")
        filename = "".join(
            random.choice(string.ascii_letters + string.digits) for i in range(10)
        )
        ext = url.split(".")[-1]

        fname = f"{filename}.{ext}"
        os.system(f"mkdir -p {storage_loc}")
        with open(storage_loc + fname, "wb") as f:
            f.write(requests.get(url).content)

        t = Tag(tag_name, "picture", fname, "", storage)
        t.save()
        return t

    @staticmethod
    def create_text(tag_name: str, content: str, storage):
        if tag_name in storage:
            raise NameError(f"Tag with name {repr(tag_name)} alrady exists!")
        t = Tag(tag_name, "text", None, content, storage)
        t.save()
        return t


def save_picture(url, tag_name, message, storage, storage_loc):
    try:
        Tag.create_picture(tag_name, url, storage, storage_loc)
    except NameError as e:
        message(str(e))
    except:
        import traceback

        traceback.print_exc()
        del storage[tag_name]


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
        paged_content = paged.element(
            sorted(f"`{el}`" for el in sorted(list(storage))),
            async_send_message,
            description="Tags:",
            max_lines=100,
            with_quotes=False,
            no_timeout=True,
            line_separator=", ",
        )
        await paged_content.get_crt_page()
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
        return "Done"
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
