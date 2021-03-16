import spanky.utils.discord_utils as dutils
from discord import AllowedMentions

from spanky.plugin.permissions import Permission
from spanky.plugin import hook, permissions


@hook.command(permissions=Permission.admin)
async def say(text, server, event, async_send_message):
    """
    <channel message> - Send a message to a channel
    """
    data = text.split(" ", maxsplit=1)
    channel = dutils.get_channel_by_id(server, dutils.str_to_id(data[0]))

    if not channel:
        return "Invalid channel"

    print(channel.name)

    await async_send_message(text=data[1], target=channel.id, allowed_mentions=AllowedMentions.all())
