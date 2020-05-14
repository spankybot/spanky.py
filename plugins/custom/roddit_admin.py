import datetime
import spanky.utils.time_utils as time_utils
import spanky.utils.discord_utils as dutils

from spanky.plugin import hook
from spanky.utils import time_utils
from spanky.plugin.event import EventType
from spanky.plugin.permissions import Permission
from plugins.temp_role import assign_temp_role, check_exp_time, get_reasons

RODDIT_ID = "287285563118190592"

@hook.command(server_id=RODDIT_ID)
async def votat(author, event, server):
    role = dutils.get_role_by_name(server, "A votat")
    author.add_role(role)

    try:
        await event.msg.async_add_reaction(u"👍")
    except:
        import traceback
        traceback.print_exc()

@hook.event(EventType.join)
def auto_ok(server, event, send_message, storage):
    if server.id != RODDIT_ID:
        return

    creation_date = datetime.datetime.utcfromtimestamp(
        int((int(event.member.id) >> 22) + 1420070400000) / 1000)
    age = (datetime.datetime.now() - creation_date).total_seconds()

    abulau = storage["join_params"]["abulau"]
    avaloare = storage["join_params"]["aval"]

    if age < abulau:
        role = dutils.get_role_by_name(server, "Bulău")
        event.member.add_role(role)
        send_message(target="449899630176632842",
                     text="Auto-bulau given to <@%s>" % event.member.id)
    elif age < avaloare:
        send_message(target="449899630176632842",
                     text="Auto-valoare not given to <@%s>" % event.member.id)
    else:
        role = dutils.get_role_by_name(server, "Valoare")
        event.member.add_role(role)
        send_message(target="449899630176632842",
                     text="Auto-valoare given to <@%s>" % event.member.id)

@hook.command(permissions=Permission.admin, server_id=RODDIT_ID)
def get_auto_valoare(storage):
    if "join_params" not in storage:
        return "No value set"

    if "aval" not in storage["join_params"]:
        return "No value set"

    return time_utils.sec_to_human(storage["join_params"]["aval"])

@hook.command(permissions=Permission.admin, server_id=RODDIT_ID)
def set_auto_valoare(storage, text):
    """
    Set auto valoare to a timeout value (e.g. 10h - 10 hours, 100d - 100 days, etc.).
    """
    if "join_params" not in storage:
        storage["join_params"] = {}

    storage["join_params"]["aval"] = time_utils.timeout_to_sec(text)
    storage.sync()

    return "Set to %s" % time_utils.sec_to_human(storage["join_params"]["aval"])

@hook.command(permissions=Permission.admin, server_id=RODDIT_ID)
def get_auto_bulau(storage):
    if "join_params" not in storage:
        return "No value set"

    if "abulau" not in storage["join_params"]:
        return "No value set"

    return time_utils.sec_to_human(storage["join_params"]["abulau"])

@hook.command(permissions=Permission.admin, server_id=RODDIT_ID)
def set_auto_bulau(storage, text):
    """
    Set auto bulau to a timeout value (e.g. 10h - 10 hours, 100d - 100 days, etc.).
    """
    if "join_params" not in storage:
        storage["join_params"] = {}

    storage["join_params"]["abulau"] = time_utils.timeout_to_sec(text)
    storage.sync()

    return "Set to %s" % time_utils.sec_to_human(storage["join_params"]["abulau"])

@hook.command(permissions=Permission.admin, server_id=RODDIT_ID)
async def ok(event, text, str_to_id, server):
    try:
        role = dutils.get_role_by_name(server, "Valoare")
        user = dutils.get_user_by_id(server, str_to_id(text))

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

        if len(user.roles) == 1 and user.roles[0].id == "688168479018451081":
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
        if len(user.roles) == 0 or (len(user.roles) == 1 and user.roles[0].id == "688168479018451081"):
            reply("Kicking <@%s>" % user.id)

            user.kick()


@hook.command(permissions=Permission.admin, server_id=RODDIT_ID)
async def list_joins_between(server, text, async_send_message):
    import datetime
    import spanky.utils.formatting as fmt
    text = text.split(" ")

    if len(text) != 2:
        return "Needs before and after: `.list_joins_between 2020-01-02 2020-01-03`"

    d1 = datetime.datetime.strptime(text[0], "%Y-%m-%d")
    d2 = datetime.datetime.strptime(text[1], "%Y-%m-%d")

    users = get_joins_between(server, d1, d2)

    msg_ret = ""

    for user in users:
        msg_ret += "<@%s> " % user.id

    msg_lst = [msg_ret]
    if len(msg_ret) > 2000:
        msg_lst = fmt.chunk_str(msg_ret)

    for msg in msg_lst:
        await async_send_message(msg)


@hook.periodic(interval=60 * 60)
def assign_old(bot):
    server = None
    for srv in bot.backend.get_servers():
        if srv.id == RODDIT_ID:
            server = srv
            break

    import datetime
    now = datetime.datetime.now()

    two_weeks = now - datetime.timedelta(days=14)
    joins_2weeks = get_joins_between(server, two_weeks, now)
    joins_2weeks_ids = [usr.id for usr in joins_2weeks]

    joinrole = dutils.get_role_by_id(server, "688168479018451081")

    for user in server.get_users():
        has_role = False
        for role in user.roles:
            if role.id == joinrole.id:
                has_role = True
                break

        if has_role:
            if user.id not in joins_2weeks_ids:
                print("remove " + str(user.id))
                user.remove_role(joinrole)


def get_joins_between(server, d1, d2):
    users = []
    for user in server.get_users():
        if user._raw.joined_at >= d1 and user._raw.joined_at < d2:
            users.append(user)

    return users
