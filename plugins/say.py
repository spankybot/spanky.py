import spanky.utils.discord_utils as dutils
from discord import AllowedMentions

from spanky.plugin.permissions import Permission
from spanky.plugin import hook, permissions


@hook.command(permissions=Permission.admin)
async def say(text, server, async_send_message):
    """
    <channel message> - Send a message to a channel
    """
    data = text.split(" ", maxsplit=1)
    channel = dutils.get_channel_by_id(server, dutils.str_to_id(data[0]))

    if not channel:
        return "Invalid channel"

    await async_send_message(
        text=data[1], target=channel.id, allowed_mentions=AllowedMentions.all()
    )


@hook.command(permissions=Permission.admin)
def say_pm(text, bot):
    """
    <user message> - Send a message to an user.
    """
    data = text.split(" ", maxsplit=1)
    user_id = dutils.str_to_id(data[0])

    user = None
    for server in bot.backend.get_servers():
        user = dutils.get_user_by_id(server, user_id)
        if user:
            break

    if not user:
        return "Invalid user"

    user.send_pm(data[1])
    return "Done"
