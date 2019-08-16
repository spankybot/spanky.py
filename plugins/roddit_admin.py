import datetime
from spanky.plugin import hook
from spanky.utils import time_utils
from spanky.plugin.permissions import Permission
from plugins.temp_role import assign_temp_role, get_rtime, check_exp_time, get_reasons
from plugins.discord_utils import *

RODDIT_ID = "287285563118190592"

roddit = None
rstorage = None

@hook.command(permissions=Permission.admin, server_id=RODDIT_ID)
def bulau(send_message, text, server, event, bot, str_to_id):
    """<user, duration (reason)> - assign bulau role for specified time - duration can be seconds, minutes, hours, days.\
 To set a 10 minute 15 seconds timeout for someone, type: '.bulau @user 10m15s'.\
 The abbrebiations are: s - seconds, m - minutes, h - hours, d - days.
    """
    ret, _ = assign_temp_role(rstorage, roddit, bot, "Bulău", text, "bulau", str_to_id, event)

    send_message(ret)

@hook.on_ready(server_id=RODDIT_ID)
def get_roddit(server, storage):
    global roddit
    global rstorage

    roddit = server
    rstorage = storage

@hook.command(server_id=RODDIT_ID)
def bulautime(text, str_to_id, storage):
    """Print remaining time in bulau"""
    return get_rtime(text, str_to_id, roddit, "bulau")

@hook.command(server_id=RODDIT_ID)
def bulaureasons(text, str_to_id, storage):
    return get_reasons(text, str_to_id, storage)

@hook.periodic(2)
def bulaucheck():
    check_exp_time(rstorage, "bulau", "Bulău", roddit)

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
