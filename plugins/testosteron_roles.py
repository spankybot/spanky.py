from plugins.discord_utils import roles_from_list
from spanky.plugin import hook

ID = "611894947024470027"

@hook.command(server_id=ID)
def testosteron(send_message, server, event, bot, text):
    return roles_from_list(
            "---START---",
            "---END---",
            "nu am coaie",
            send_message,
            server,
            event,
            bot,
            text)
