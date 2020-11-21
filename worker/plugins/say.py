import utils.discord_utils as dutils

from core.hook import Permission
from core import hook


@hook.command(permissions=Permission.admin)
def say(text, server, event, send_message):
    """
    <channel message> - Send a message to a channel
    """
    data = text.split(" ", maxsplit=1)

    send_message(text=data[1], channel_id=dutils.str_to_id(data[0]))
