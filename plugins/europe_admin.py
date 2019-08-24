import datetime
import plugins.paged_content as paged
from collections import deque
from spanky.plugin import hook
from spanky.utils import time_utils
from spanky.plugin.event import EventType
from spanky.plugin.permissions import Permission
from plugins.temp_role import assign_temp_role, get_rtime, check_exp_time, get_reasons, close_case
from plugins.discord_utils import roles_from_list, remove_role_from_list, add_role_from_list, remove_given_role_from_list

time_tokens = ['s', 'm', 'h', 'd']
SEC_IN_MIN = 60
SEC_IN_HOUR = SEC_IN_MIN * 60
SEC_IN_DAY = SEC_IN_HOUR * 24

EUROPE_ID = "258012752629596161"

roddit = None
rstorage = None
spam_check = {}
SPAM_LIMIT = 4

@hook.event(EventType.message, server_id=EUROPE_ID)
def check_spam(bot, event, send_pm, str_to_id, send_message):
    if event.author.bot:
        return

    if event.author.id not in spam_check:
        spam_check[event.author.id] = deque(maxlen=SPAM_LIMIT)

    spam_check[event.author.id].append((datetime.datetime.utcnow(), event.msg.text))

    if len(spam_check[event.author.id]) == SPAM_LIMIT and \
        (spam_check[event.author.id][-1][0] - spam_check[event.author.id][0][0]).total_seconds() < 10:
            ftext = spam_check[event.author.id][0][1]

            for i in range(1, SPAM_LIMIT):
                if ftext != spam_check[event.author.id][i][1]:
                    return

            spam_check[event.author.id] = deque(maxlen=SPAM_LIMIT)
            send_pm("You have been muted in the %s server for spamming with `%s`\nYour confinement will last for one hour." % (event.server.name, ftext),
                event.author)

            print(ftext)

            ret, reason = assign_temp_role(
                rstorage,
                roddit,
                bot,
                "Temporary Confinement",
                "<@%s> 1h Spamming with `%s`" % (event.author.id, ftext),
                "confine",
                str_to_id,
                event)

            if reason:
                mod_action_text = "-\n"
                for k, v in reason.items():
                    mod_action_text += "**%s:** %s\n" % (k, v)

                send_message(text=mod_action_text, target="#mod-actions")

            send_message(ret)

@hook.command(permissions=Permission.admin, server_id=EUROPE_ID)
def gulag(send_message, text, server, event, bot, str_to_id):
    """<user, duration> - assign gulag role for specified time - duration can be seconds, minutes, hours, days.\
 To set a 10 minute 15 seconds timeout for someone, type: '.gulag @user 10m15s'.\
 The abbrebiations are: s - seconds, m - minutes, h - hours, d - days.
    """
    ret, reason = assign_temp_role(rstorage, roddit, bot, "Gulag", text, "gulag", str_to_id, event)

    if reason:
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
def expire_check():
    check_exp_time(rstorage, "gulag", "Gulag", roddit)
    check_exp_time(rstorage, "confine", "Temporary Confinement", roddit)

@hook.command(server_id=EUROPE_ID)
async def userhistory(text, str_to_id, storage, async_send_message):
    """<user> - List gulag/confine reasons for user"""
    try:
        usr_hist = get_reasons(text, str_to_id, storage)
        if type(usr_hist) == str:
            usr_hist = [usr_hist]

        paged_content = paged.element(usr_hist, async_send_message, "User history:", no_timeout=True)
        await paged_content.get_crt_page()
    except:
        import traceback
        traceback.print_exc()

@hook.command(permissions=Permission.admin, server_id=EUROPE_ID)
def confine(send_message, text, server, event, bot, str_to_id):
    """<user, duration> - assign confinment role for specified time - duration can be seconds, minutes, hours, days.\
 To set a 10 minute 15 seconds timeout for someone, type: '.confine @user 10m15s'.\
 The abbrebiations are: s - seconds, m - minutes, h - hours, d - days.
    """
    ret, reason = assign_temp_role(rstorage, roddit, bot, "Temporary Confinement", text, "confine", str_to_id, event)

    if reason:
        gulag_text = "-\n"
        for k, v in reason.items():
            gulag_text += "**%s:** %s\n" % (k, v)

        send_message(text=gulag_text, target="#mod-actions")
    send_message(ret)

@hook.command(permissions=Permission.admin, server_id=EUROPE_ID)
def close_user_case(send_message, text):
    """
    <case ID> - Close a case ID
    """

    rtext = close_case(text, rstorage)

    send_message(rtext)

@hook.command(server_id=EUROPE_ID)
def country(send_message, server, event, bot, text):
    """
    **.country**  |  Lists all self-assignable countries (you are limited to one at a time)
    **.country** `name`  |  Assigns you the chosen country (retyping the command with a different country will replace the current one)
    **.nocountry**  |  Removes your country role
    """
    return roles_from_list(
            "▼ COUNTRIES ▼",
            "▲ COUNTRIES ▲",
            None,
            send_message,
            server,
            event,
            bot,
            text)

@hook.command(server_id=EUROPE_ID)
def nocountry(send_message, server, event):
    """Remove all country roles"""
    return remove_role_from_list(
            "▼ COUNTRIES ▼",
            "▲ COUNTRIES ▲",
            server,
            event,
            send_message)


@hook.command(server_id=EUROPE_ID)
def assign(send_message, server, event, text):
    """
    **.assign**  |  Lists all self-assignable roles
    **.assign** `name`  |  Assigns you the chosen role
    **.unassign** `name` | Unassigns the given role
    """
    return add_role_from_list(
            "▼ ASSIGNABLE ▼",
            "▲ ASSIGNABLE ▲",
            server,
            event,
            send_message,
            text)

@hook.command(server_id=EUROPE_ID)
def unassign(send_message, server, event, text):
    """
    Unassigns a given role
    """
    return remove_given_role_from_list(
            "▼ ASSIGNABLE ▼",
            "▲ ASSIGNABLE ▲",
            server,
            event,
            send_message,
            text)
