import subprocess
import utils.discord_utils as dutils

from utils import time_utils
from core import hook


@hook.command()
def remind(event, text, storage):
    """<period message> - ask the bot to remind you about something in given period (e.g. '.remind 1h bleh bleh' sends you 'bleh bleh' in one hour"""

    # Get period and message
    data = text.split(" ", maxsplit=1)

    if len(data) != 2:
        return "Must specify period and message"

    # Extract all the data
    remind_seconds = time_utils.timeout_to_sec(data[0])
    message = data[1]

    if "remind" not in storage:
        storage["remind"] = []

    # Create new entry
    elem = {}
    elem["author"] = event.author.id
    elem["deadline"] = time_utils.tnow() + remind_seconds
    elem["message"] = message

    # Append it to the reminder list
    storage["remind"].append(elem)

    # Save it
    storage.sync()

    return "Okay!"


def remind_check_server(server, storage, send_pm):
    if "remind" not in storage:
        return

    # Parse list
    for elem in storage["remind"]:
        # Check if expired
        if elem["deadline"] < time_utils.tnow():
            # Remove it from list
            storage["remind"].remove(elem)
            storage.sync()

            # Get target user
            target_user = dutils.get_user_by_id(server, elem["author"])
            if not target_user:
                print("invalid user")
                continue

            send_pm("You set a reminder with the message:\n%s" %
                    elem["message"], target_user)


@hook.periodic(1)
def remind_check(bot, send_pm):
    for server in bot.backend.get_servers():
        storage = bot.server_permissions[server.id].get_plugin_storage_raw(
            "plugins_remind.json")

        remind_check_server(server, storage, send_pm)
