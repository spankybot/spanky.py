import datetime
from spanky.plugin import hook
from spanky.utils import time_utils
from spanky.plugin.event import EventType
from spanky.plugin.permissions import Permission
from plugins.temp_role import assign_temp_role, get_rtime, check_exp_time, get_reasons
from plugins.discord_utils import *

RODDIT_ID = "287285563118190592"

@hook.command
async def votat(author, event):
    role = get_role_by_name(roddit, "A votat")
    author.add_role(role)

    try:
        await event.msg.async_add_reaction(u"👍")
    except:
        import traceback
        traceback.print_exc()

@hook.command(permissions=Permission.admin, server_id=RODDIT_ID)
async def ok(event, text, str_to_id):
    role = get_role_by_name(roddit, "Valoare")
    user = get_user_by_id(roddit, str_to_id(text))

    await event.msg.async_add_reaction(u"👍")

    user.add_role(role)

@hook.command(permissions=Permission.admin, server_id=RODDIT_ID)
def list_noobs(reply):
    noobs = []
    users = roddit.get_users()

    for user in users:
        if len(user.roles) == 0:
            noobs.append(user.id)

    msg = ""
    for noob in noobs:
        msg += "<@" + noob + "> \n"

        if len(msg) > 1000:
            reply(msg)
            msg = ""

    reply(msg)

@hook.command(permissions=Permission.admin, server_id=RODDIT_ID)
def kick_noobs(reply):
    users = roddit.get_users()

    for user in users:
        if len(user.roles) == 0:
            reply("Kicking <@%s>" % user.id)

            user.kick()

@hook.event(EventType.reaction_add)
async def rem_invalid(event):
    if event.channel.id != "620225520608739348":
        return
    try:
        if event.reaction.emoji.name != u"👍":
            await event.msg.async_remove_reaction(event.reaction.emoji._raw, event.author)
    except:
        import traceback
        traceback.print_exc()

@hook.event(EventType.message)
async def concurs(event):
    if event.channel.id == "620225520608739348":
        await event.msg.async_add_reaction(u"👍")
