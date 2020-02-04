import datetime
from spanky.plugin import hook
from spanky.utils import time_utils
from spanky.plugin.event import EventType
from spanky.plugin.permissions import Permission
from plugins.temp_role import assign_temp_role, get_rtime, check_exp_time, get_reasons
from plugins.discord_utils import *

RODDIT_ID = "287285563118190592"

@hook.command
async def votat(author, event, server):
    role = get_role_by_name(server, "A votat")
    author.add_role(role)

    try:
        await event.msg.async_add_reaction(u"👍")
    except:
        import traceback
        traceback.print_exc()

@hook.command(permissions=Permission.admin, server_id=RODDIT_ID)
async def ok(event, text, str_to_id, server):
    try:
        role = get_role_by_name(server, "Valoare")
        user = get_user_by_id(server, str_to_id(text))

        await event.msg.async_add_reaction(u"👍")

        user.add_role(role)
    except:
        import traceback
        traceback.print_exc()

@hook.command(permissions=Permission.admin, server_id=RODDIT_ID)
def list_noobs(reply, server):
    noobs = []
    users = server.get_users()

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
def kick_noobs(reply, server):
    users = server.get_users()

    for user in users:
        if len(user.roles) == 0:
            reply("Kicking <@%s>" % user.id)

            user.kick()