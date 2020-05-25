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

@hook.command(server_id=RODDIT_ID)
async def gibcolor(async_send_message, send_message, event):
    sel = selector.RoleSelectorInterval(
        server=event.server,
        channel=event.channel,
        title="r/Romania culori",
        first_role="Albastru canar",
        last_role="Verde mușchi",
        max_selectable=1)
    await sel.do_send(event)

@hook.command(server_id=RODDIT_ID)
async def gibrole(async_send_message, send_message, event):
    sel = selector.RoleSelectorInterval(
        server=event.server,
        channel=event.channel,
        title="r/Romania roles",
        first_role="Gospodar",
        last_role="♿",
        max_selectable=5)

    await sel.do_send(event)
