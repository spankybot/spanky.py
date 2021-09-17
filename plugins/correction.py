# -*- coding: utf-8 -*-
from spanky.plugin import hook
import re2
from spanky.plugin.permissions import Permission
ELEVATED_PERMS = [Permission.admin, Permission.bot_owner]

MAX_LEN = 50

@hook.command(permissions=ELEVATED_PERMS)
def toggle_correction_msg_del_ability(storage, event):
    """enable/disable ability for automatic deletion of command when running .s/.ss"""
    if "disabled" not in storage:
        storage["disabled"] = True

    newVal = not storage["disabled"]
    storage["disabled"] = newVal
    storage.sync()

    if newVal:
        return "Users now cannot auto-delete messages"
    else:
        return "Users can now auto-delete messages"

@hook.command()
def toggle_correction_msg_del(storage, event):
    """enable/disable automatic deletion of command when running .s/.ss"""
    if "disabled" not in storage:
        storage["disabled"] = True
    if storage["disabled"]:
        return "Function disabled."
    if "prefs" not in storage:
        storage["prefs"] = {}

    if event.author.id not in storage["prefs"]:
        storage["prefs"][event.author.id] = False

    newVal = not storage["prefs"][event.author.id]
    storage["prefs"][event.author.id] = newVal
    storage.sync()

    if newVal:
        return "I will now auto-delete your commands"
    else:
        return "I will no longer auto-delete your commands"

def delete_if_needed(storage, event):
    if "disabled" not in storage:
        storage["disabled"] = True
    if storage["disabled"]:
        return
    if "prefs" not in storage:
        storage["prefs"] = {}
    if event.author.id not in storage["prefs"]:
        storage["prefs"][event.author.id] = False

    if storage["prefs"][event.author.id]:
        event.msg.delete_message()


def find_best_match(word_list, message):
    """
    Finds the largest element subset that's present in a message.
    """

    list_idx = 0
    while " ".join(word_list[0:list_idx + 1]) in message:
        list_idx += 1

    return list_idx


@hook.command()
async def s(text, channel, reply, event, bot, storage):
    """<word replacement> - replace 'word' with replacement"""

    delete_if_needed(storage, event)

    split_text = text.split()
    if len(split_text) == 0:
        msg = "Invalid format"
        msg += ": " + "\n`" + "<word replacement> - replace 'word' with replacement`"
        msg += "\n`" + "if only one word is specified, it will be replaced with a blankspace`"
        reply(msg, timeout=15)
        return

    if len(split_text) == 1:
        split_text.append("")

    replied_to = await event.msg.reference()
    if replied_to:
        messages = [replied_to]
    else:
        messages = await channel.async_get_latest_messages(MAX_LEN)

    for msg in messages:
        if msg.id == event.msg.id or msg.author.id == bot.get_own_id() or msg.text.startswith(".s"):
            continue

        msg_index = find_best_match(split_text, msg.text)

        if msg_index > 0:
            final_text = msg.text.replace(
                " ".join(split_text[0:msg_index]),
                " ".join(split_text[msg_index:]))

            msg = "<%s> %s" % (msg.author.name, final_text)
            reply(msg)
            return



@hook.command()
async def ss(text, channel, reply, event, bot, storage):
    """<regex replacement> - replace regex with replacement"""

    delete_if_needed(storage, event)

    text = text.split(maxsplit=1)
    if len(text) == 0 or len(text) > 2:
        msg = "Invalid format"
        msg += ": " + "\n`" + "<regex replacement> - replace regex with replacement`"
        msg += "\n`" + "if only the regex is specified, it will be replaced with a blankspace`"
        reply(msg, timeout=15)
        return

    if len(text) == 1:
        text.append("")

    replied_to = await event.msg.reference()
    if replied_to:
        messages = [replied_to]
    else:
        messages = await channel.async_get_latest_messages(MAX_LEN)

    try:
        regex = re2.compile(text[0])
    except:
        reply("You don't have a valid regex")
        return

    for msg in messages:
        if msg.id == event.msg.id or msg.author.id == bot.get_own_id() or msg.text.startswith(".s"):
            continue
        if regex.search(msg.text) != None:
            msg = "<%s> %s" % (msg.author.name, regex.sub(text[1], msg.text))
            reply(msg)
            return
