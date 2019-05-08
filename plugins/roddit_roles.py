from plugins.discord_utils import roles_from_list
from spanky.plugin import hook

RODDIT_ID = "287285563118190592"

@hook.command(server_id=RODDIT_ID)
def color(send_message, server, event, bot, text):
    return roles_from_list(
            "- START Culori -",
            "- END Culori -",
            "nu vreau culoare",
            send_message,
            server,
            event,
            bot,
            text)

@hook.command(server_id=RODDIT_ID)
def joc(send_message, server, event, bot, text):
    return roles_from_list(
            "- START Jocuri -",
            "- END Jocuri -",
            "nu vreau joc",
            send_message,
            server,
            event,
            bot,
            text)

@hook.command(server_id=RODDIT_ID)
def rol(send_message, server, event, bot, text):
    return roles_from_list(
            "- START Grupuri -",
            "- END Grupuri -",
            "nu vreau",
            send_message,
            server,
            event,
            bot,
            text)
