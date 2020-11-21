import datetime
import plugins.paged_content as paged
from collections import deque
from core import hook
from utils import time_utils
from core.event import EventType
from hook.permissions import Permission
from plugins.temp_role import assign_temp_role, check_exp_time, get_reasons
from utils.discord_utils import roles_from_list, remove_role_from_list, add_role_from_list, remove_given_role_from_list

EUROPE_ID = "258012752629596161"

spam_check = {}
SPAM_LIMIT = 4

# @hook.event(EventType.message, server_id=EUROPE_ID)
# def check_spam(bot, event, send_pm, str_to_id, send_message, send_embed):
#     if event.author.bot:
#         return

#     if event.author.id not in spam_check:
#         spam_check[event.author.id] = deque(maxlen=SPAM_LIMIT)

#     spam_check[event.author.id].append(
#         (datetime.datetime.utcnow(), event.msg.text))

#     if len(spam_check[event.author.id]) == SPAM_LIMIT and \
#             (spam_check[event.author.id][-1][0] - spam_check[event.author.id][0][0]).total_seconds() < 10:
#         ftext = spam_check[event.author.id][0][1]

#         for i in range(1, SPAM_LIMIT):
#             if ftext != spam_check[event.author.id][i][1]:
#                 return

#         spam_check[event.author.id] = deque(maxlen=SPAM_LIMIT)
#         send_pm("You have been muted in the %s server for spamming with `%s`\nYour confinement will last for one hour." % (event.server.name, ftext),
#                 event.author)

#         ret, reason = assign_temp_role(
#             rstorage,
#             roddit,
#             bot,
#             "Temporary Confinement",
#             "<@%s> 1h Spamming with `%s`" % (event.author.id, ftext),
#             "confine",
#             str_to_id,
#             event)

#         if reason:
#             mod_action_text = "-\n"
#             for k, v in reason.items():
#                 mod_action_text += "**%s:** %s\n" % (k, v)

#             send_embed("User confined for spam", "", {
#                        "Details": mod_action_text}, target="#mod-actions")

#         send_message(ret)


@hook.command(server_id=EUROPE_ID)
def country(send_message, server, event, bot, text):
    """
    **.country**  |  Lists all self-assignable countries
    **.country** `name`  |  Assigns you the chosen country (retyping the command with a different country will give you another country role)
    **.nocountry** `name`  |  Removes a country role
    """
    return add_role_from_list(
        "▼ COUNTRIES ▼",
        "▲ COUNTRIES ▲",
        server,
        event,
        send_message,
        text,
        max_assignable=2)


@hook.command(server_id=EUROPE_ID)
def nocountry(send_message, server, event, text):
    """
    **.nocountry** `name` | Remove a given country
    """
    return remove_given_role_from_list(
        "▼ COUNTRIES ▼",
        "▲ COUNTRIES ▲",
        server,
        event,
        send_message,
        text)


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


@hook.command(server_id=EUROPE_ID)
def iam():
    return "That command is deprecated, use `.assign` or `.country` to self-assign a role."
