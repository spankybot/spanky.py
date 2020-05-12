from plugins.discord_utils import roles_from_list
from spanky.plugin import hook

ROBAC_ID = "456496203040030721"

@hook.command(server_id=ROBAC_ID)
def tara(send_message, server, event, bot, text):
    return roles_from_list(
            "-----[Countries]-----",
            "-----<Countries/>-----",
            "nu vreau",
            send_message,
            server,
            event,
            bot,
            text)

@hook.command(server_id=ROBAC_ID)
def am_luat(send_message, server, event, bot, text):
    return roles_from_list(
            "-----[Bac]-----",
            "-----<Bac/>-----",
            "nu vreau",
            send_message,
            server,
            event,
            bot,
            text)
