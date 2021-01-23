from SpankyWorker import hook
import SpankyWorker.utils.time_utils as tutils


@hook.command()
def remind(event, text, storage):
    """
    <period message> - ask the bot to remind you about something in given period (e.g. '.remind 1h bleh bleh' sends you 'bleh bleh' in one hour
    """

    # Get period and message
    data = text.split(" ", maxsplit=1)

    if len(data) != 2:
        return "Must specify period and message"

    # Extract all the data
    remind_seconds = tutils.timeout_to_sec(data[0])
    message = data[1]

    if "remind" not in storage:
        storage["remind"] = []

    # Create new entry
    elem = {}
    elem["author"] = event.author.id
    elem["deadline"] = tutils.tnow() + remind_seconds
    elem["message"] = message

    # Append it to the reminder list
    storage["remind"].append(elem)

    # Save it
    storage.sync()

    return "Okay!"


def remind_check_server(server, storage):
    if "remind" not in storage:
        return

    # Parse list
    for elem in storage["remind"]:
        # Check if expired
        if elem["deadline"] < tutils.tnow():
            # Remove it from list
            storage["remind"].remove(elem)
            storage.sync()

            # Get target user
            target_user = server.get_user(user_id=elem["author"])
            if not target_user:
                print("invalid user")
                continue

            target_user.send_pm(
                "You set a reminder with the message:\n%s" % elem["message"])


@hook.periodic(1)
def remind_check(connected_servers, plugin_name):
    for server in connected_servers():
        storage = server.get_plugin_storage(plugin_name)

        remind_check_server(server, storage)
