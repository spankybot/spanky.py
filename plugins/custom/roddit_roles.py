from spanky.utils.discord_utils import add_role_from_list, remove_role_from_list, roles_from_list, remove_given_role_from_list, user_roles_from_list
from spanky.plugin import hook

RODDIT_ID = "287285563118190592"

@hook.command(server_id=RODDIT_ID)
def vreau_culoare(send_message, server, event, text, bot):
    return roles_from_list(
            "----- START Culori -----",
            "------- END Culori -------",
            None,
            send_message,
            server,
            event,
            bot,
            text)

@hook.command(server_id=RODDIT_ID)
def nu_vreau_culoare(send_message, server, event, text):
    return remove_role_from_list(
            "----- START Culori -----",
            "------- END Culori -------",
            server,
            event,
            send_message)

@hook.command(server_id=RODDIT_ID)
def vreau_joc(send_message, server, event, text):
    return add_role_from_list(
            "---- START Jocuri ----",
            "---- END Jocuri ----",
            server,
            event,
            send_message,
            text)

@hook.command(server_id=RODDIT_ID)
def nu_vreau_joc(send_message, server, event, text):
    return remove_given_role_from_list(
            "---- START Jocuri ----",
            "---- END Jocuri ----",
            server,
            event,
            send_message,
            text)

@hook.command(server_id=RODDIT_ID)
def vreau_rol(send_message, server, event, bot, text):
    return add_role_from_list(
            "---- START Grupuri ----",
            "---- END Grupuri ----",
            server,
            event,
            send_message,
            text)

@hook.command(server_id=RODDIT_ID)
def nu_vreau_rol(send_message, server, event, bot, text):
    return remove_given_role_from_list(
            "---- START Grupuri ----",
            "---- END Grupuri ----",
            server,
            event,
            send_message,
            text)

import plugins.selector as selector
from spanky.utils.discord_utils import get_roles_between
from collections import OrderedDict
import spanky.utils.time_utils as tutils

MIN_SEC = 3
MSG_TIMEOUT = 3
last_user_assign = {}

@hook.command(server_id=RODDIT_ID)
async def gibrole(async_send_message, send_message, server):
    roles = get_roles_between(
            "----- START Culori -----",
            "------- END Culori -------",
            server)

    role_list = OrderedDict()
    max_per_lst = 1
    for role in roles:
        async def assign_role(event, the_role=role, rlist=roles, max_lst=max_per_lst, async_send_message=async_send_message):
            # Check role assign spam
            now = tutils.tnow()
            if event.author.id in last_user_assign and now - last_user_assign[event.author.id] < MIN_SEC:
                last_user_assign[event.author.id] = now
                event.author.send_pm("You're assigning roles too quickly. You need to wait %d seconds between assignments" % MIN_SEC)
                return

            print("Assign %s" % the_role.name)
            last_user_assign[event.author.id] = now

            crt_roles = user_roles_from_list(event.author, rlist)
            # Check if the user already has the role so that we remove it
            for crt in crt_roles:
                if the_role.id == crt.id:
                    event.author.remove_role(the_role)
                    return

            # Remove extra roles
            removed = []
            if len(crt_roles) >= max_lst:
                # +1 to make room for another
                for i in range(len(crt_roles) - max_lst + 1):
                    event.author.remove_role(crt_roles[i])
                    removed.append(crt_roles[i].name)

            event.author.add_role(the_role)
            reply_msg = "Added: %s" % the_role.name
            if len(removed) > 0:
                reply_msg += " || Removed: %s" % ", ".join(removed)
                await async_send_message("<@%s>: `%s`" % (event.author.id, reply_msg), timeout=MSG_TIMEOUT, check_old=False)

        role_list["%s" % role.name] = assign_role

    sel = selector.Selector(title="r/Romania roles", footer="Max. selectable %d" % max_per_lst, async_send_message=async_send_message, call_dict=role_list, paged=True)
    await sel.do_send()
