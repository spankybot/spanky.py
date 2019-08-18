import datetime
from collections import deque
from spanky.plugin import hook
from spanky.utils import time_utils
from spanky.plugin.event import EventType
from spanky.plugin.permissions import Permission
from plugins.temp_role import assign_temp_role, get_rtime, check_exp_time, get_reasons

time_tokens = ['s', 'm', 'h', 'd']
SEC_IN_MIN = 60
SEC_IN_HOUR = SEC_IN_MIN * 60
SEC_IN_DAY = SEC_IN_HOUR * 24

EUROPE_ID = "258012752629596161"

roddit = None
rstorage = None
spam_check = {}

@hook.event(EventType.message)
def check_spam(bot, event):
    if event.author.id not in spam_check:
        spam_check[event.author.id] = deque(maxlen=4)

    spam_check[event.author.id].append(datetime.datetime.utcnow())

    if len(spam_check[event.author.id]) == 4 and \
        (spam_check[event.author.id][-1] - spam_check[event.author.id][0]).total_seconds() < 10:
            print(spam_check[event.author.id])

@hook.command(permissions=Permission.admin, server_id=EUROPE_ID)
def gulag(send_message, text, server, event, bot, str_to_id):
    """<user, duration> - assign gulag role for specified time - duration can be seconds, minutes, hours, days.\
 To set a 10 minute 15 seconds timeout for someone, type: '.gulag @user 10m15s'.\
 The abbrebiations are: s - seconds, m - minutes, h - hours, d - days.
    """
    ret, reason = assign_temp_role(rstorage, roddit, bot, "Gulag", text, "gulag", str_to_id, event)

    gulag_text = "-\n"
    for k, v in reason.items():
        gulag_text += "**%s:** %s\n" % (k, v)

    send_message(text=gulag_text, target="#mod-actions")
    send_message(ret)

@hook.on_ready(server_id=EUROPE_ID)
def get_roddit(server, storage):
    global roddit
    global rstorage

    roddit = server
    rstorage = storage

@hook.command(server_id=EUROPE_ID)
def gulagtime(text, str_to_id, storage):
    """Print remaining time in gulag"""
    return get_rtime(text, str_to_id, rstorage, "gulag")

@hook.periodic(2)
def gulagcheck():
    check_exp_time(rstorage, "gulag", "Gulag", roddit)

@hook.command(server_id=EUROPE_ID)
def gulagreasons(text, str_to_id, storage):
    """<user> - List gulag reasons for user"""
    return get_reasons(text, str_to_id, storage)
