from SpankyWorker import hook
from SpankyWorker import Permission


@hook.command(permissions=Permission.admin, format="number")
async def delete(event, send_message, text):
    """
    <number> - delete a given number of messages from the channel where the \
command is executed
    """
    args = text.split()
    no_msgs = 0
    try:
        no_msgs = int(args[0])
    except:
        send_message(delete.__doc__)
        return

    if no_msgs > 1000:
        send_message("Delete less than 1000, please")
        return

    await event.discord.channel.purge(limit=no_msgs)
