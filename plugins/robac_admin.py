import datetime
from spanky.plugin import hook
from spanky.utils import time_utils
from spanky.plugin.permissions import Permission
from plugins.discord_utils import *

time_tokens = ['s', 'm', 'h', 'd']
SEC_IN_MIN = 60
SEC_IN_HOUR = SEC_IN_MIN * 60
SEC_IN_DAY = SEC_IN_HOUR * 24

ROBAC_ID = "456496203040030721"

roddit = None
rstorage = None

@hook.command(permissions=Permission.admin, server_id=ROBAC_ID)
def detentie(send_message, text, server, event, bot, str_to_id):
    """<user, duration> - assign bulau role for specified time - duration can be seconds, minutes, hours, days.\
 To set a 10 minute 15 seconds timeout for someone, type: '.bulau @user 10m15s'.\
 The abbrebiations are: s - seconds, m - minutes, h - hours, d - days.
    """
    while "  " in text:
        text = text.replace("  ", " ")

    data = text.split(" ")
    if len(data) != 2:
        send_message("Needs both user and time (e.g. .bulau @plp, 5m - to give @plp the role for 5 minutes")
        return

    user = str_to_id(data[0])
    stime = data[1]

    total_seconds = 0

    last_start = 0
    for pos, char in enumerate(stime):
        if char in time_tokens:
            value = int(stime[last_start:pos])
            if char == 's':
                total_seconds += value
            elif char == 'm':
                total_seconds += value * SEC_IN_MIN
            elif char == 'h':
                total_seconds += value * SEC_IN_HOUR
            elif char == 'd':
                total_seconds += value * SEC_IN_DAY

            last_start = pos + 1

    texp = datetime.datetime.now().timestamp() + total_seconds

    brole = get_role_by_name(server, "Detentie")
    member = get_user_by_id(server, user)

    if brole == None or member == None:
        return "Internal error."

    extra_bulau = False
    crt_roles = []

    if user in rstorage:
        extra_bulau = True

    for role in member.roles:
        if brole.id == role.id:
            print("User already in bulau")
            extra_bulau = True
            break
        crt_roles.append(role.id)

    if not extra_bulau:
        rstorage[user] = {}
        rstorage[user]["expire"] = texp
        rstorage[user]['crt_roles'] = crt_roles

        member.replace_roles([brole])

        send_message("Gave <@%s> %s seconds bulau time" % (user, str(total_seconds)))
    else:
        rstorage[user]["expire"] = texp
        send_message("Adjusted time for user to %d" % total_seconds)

    rstorage.sync()

@hook.on_ready(server_id=ROBAC_ID)
def get_roddit(server, storage):
    global roddit
    global rstorage

    roddit = server
    rstorage = storage

@hook.command(server_id=ROBAC_ID)
def detentietime(text, str_to_id, storage):
    """Print remaining time in bulau"""
    user = str_to_id(text)

    if user in storage:
        tnow = datetime.datetime.now().timestamp()
        tsec_left = storage[user]['expire'] - tnow

        return "Remaining: " + time_utils.sec_to_human(tsec_left)
    else:
        return "User not in bulau list"

@hook.periodic(2)
def detentiecheck():
    global rstorage
    tnow = datetime.datetime.now().timestamp()
    to_del = []

    if not rstorage:
        return

    for user in rstorage:
        if rstorage[user]['expire'] < tnow:
            print("Done for " + user)
            to_del.append(user)

    for user in to_del:
        role = get_role_by_name(roddit, "Bulău")
        member = get_user_by_id(roddit, user)

        new_roles = []
        for role_id in rstorage[user]['crt_roles']:
            role = get_role_by_id(roddit, role_id)
            new_roles.append(role)

        if member:
            member.replace_roles(new_roles)

        del rstorage[user]
        rstorage.sync()
