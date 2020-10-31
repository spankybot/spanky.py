import utils.discord_utils as dutils

from core.permissions import Permission
from core import hook, permissions


@hook.command(permissions=Permission.admin)
def say(text, server, event, send_message):
    """
    <channel message> - Send a message to a channel
    """
    data = text.split(" ", maxsplit=1)
    channel = dutils.get_channel_by_id(server, dutils.str_to_id(data[0]))

    if not channel:
        return "Invalid channel"

    print(channel.name)

    send_message(text=data[1], target=channel.id)
