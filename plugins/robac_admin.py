import datetime
from spanky.plugin import hook
from spanky.utils import time_utils
from spanky.plugin.permissions import Permission
from plugins.temp_role import assign_temp_role, get_rtime, check_exp_time, get_reasons, close_case

time_tokens = ['s', 'm', 'h', 'd']
SEC_IN_MIN = 60
SEC_IN_HOUR = SEC_IN_MIN * 60
SEC_IN_DAY = SEC_IN_HOUR * 24

ROBAC_ID = "456496203040030721"

roddit = None
rstorage = None

@hook.command(permissions=Permission.admin, server_id=ROBAC_ID)
def detentie(send_message, text, server, event, bot, str_to_id):
    """<user, duration> - assign detentie role for specified time - duration can be seconds, minutes, hours, days.\
 To set a 10 minute 15 seconds timeout for someone, type: '.detentie @user 10m15s'.\
 The abbrebiations are: s - seconds, m - minutes, h - hours, d - days.
    """
    ret, _ = assign_temp_role(rstorage, roddit, bot, "Detentie", text, "detentie", str_to_id, event)
    send_message(ret)

@hook.on_ready(server_id=ROBAC_ID)
def get_roddit(server, storage):
    global roddit
    global rstorage

    roddit = server
    rstorage = storage

@hook.command(server_id=ROBAC_ID)
def detentietime(text, str_to_id, storage):
    """Print remaining time in bulau"""
    return get_rtime(text, str_to_id, rstorage, "detentie")

@hook.periodic(2)
def detentiecheck():
    check_exp_time(rstorage, "detentie", "Detentie", roddit)
