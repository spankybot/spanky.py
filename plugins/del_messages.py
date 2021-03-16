from spanky.plugin import hook
from spanky.plugin.permissions import Permission


@hook.command(permissions=Permission.admin, format="number")
def delete(event, send_message, text):
    """
    <number> - delete a given number of messages from the channel where the command is executed
    """
    args = text.split()
    no_msgs = 0
    try:
        no_msgs = int(args[0])
    except:
        send_message(delete.__doc__)

    if no_msgs > 1000:
        send_message("Delete less than 1000, please")
        return

    event.channel.delete_messages(no_msgs)
