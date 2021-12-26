import datetime
from spanky.plugin import hook, permissions
from spanky.hook2.event import EventType
from spanky.plugin.permissions import Permission
from spanky.utils import time_utils
from plugins.log import get_msg_cnt_for_user
import nextcord

# I don't know any better way to do this, since it needs to auto increment in a join call


class Counter:
    def __init__(self, start=1):
        self.x = start

    def get(self):
        self.x += 1
        return self.x - 1


def find_event_by_text(storage, text, str_to_id):
    events = []
    if not "on_join" in storage:
        return events

    for item in storage["on_join"]:
        if item["type"] == "message":
            if text in item["message"]:
                events.append(item)
        elif item["type"] == "role":
            if str_to_id(text) in item["role"]:
                events.append(item)

    return events


def find_event_by_id(storage, e_id):
    if not "on_join" in storage:
        return None
    msg_events = []
    role_events = []
    cnt = Counter()

    # commands should also do this
    try:
        e_id = int(e_id)
    except ValueError:
        return None

    for item in storage["on_join"]:
        if item["type"] == "message":
            msg_events.append(item)
        elif item["type"] == "role":
            role_events.append(item)

    for event in msg_events:
        val = cnt.get()

        if e_id == val:
            return event

    for event in role_events:
        val = cnt.get()

        if e_id == val:
            return event

    return None


def find_event_by_text_match(storage, text, str_to_id):
    events = []
    if not "on_join" in storage:
        return events

    for item in storage["on_join"]:
        if item["type"] == "message":
            if text == item["message"]:
                events.append(item)
        elif item["type"] == "role":
            if str_to_id(text) == item["role"]:
                events.append(item)

    return events


@hook.command(permissions=Permission.admin)
def add_join_event(storage, text, str_to_id, id_to_chan, id_to_role_name):
    """
    <'type' 'option'> - Add action to be triggered on user join.
Possible actions:
 * message #channel blahblah -> send blahblah to #channel
 * role @role -> set @role on join).
The scripted message can contain special words that are replaced when the event is triggered:
 * {AGE} - Account age
 * {USER} - User that just joined
 * {USER_ID} - User ID
 * {SEEN_CNT} - How many times this user has been seen in servers shared with the bot

e.g. 'message #general {USER} / {USER_ID} just joined!' will send 'John / 12345678910 just joined!'
    """
    text = text.split(maxsplit=2)
    if storage["on_join"] == None:
        storage["on_join"] = []

    if text[0] == "message":
        existing = find_event_by_text_match(storage, text[2], str_to_id)
        for match in existing:
            if match["type"] == "message" and match["chan"] == str_to_id(text[1]):
                return "There already is a message with that content in that channel"

        new_entry = {}
        new_entry["chan"] = str_to_id(text[1])
        new_entry["message"] = text[2]
        new_entry["timeout"] = 0
        new_entry["type"] = "message"

        storage["on_join"].append(new_entry)
        storage.sync()

        return "OK. Will send the given on join message to " + id_to_chan(
            new_entry["chan"]
        )
    elif text[0] == "role":
        existing = find_event_by_text_match(storage, text[1], str_to_id)
        for match in existing:
            if match["type"] == "role":
                return "There already is a role event with that"

        role_name = ""
        new_entry = {}
        new_entry["type"] = "role"
        try:
            new_entry["role"] = str_to_id(text[1])
            role_name = id_to_role_name(new_entry["role"])
        except:
            return "Could not find a role by the given parameter."

        storage["on_join"].append(new_entry)
        storage.sync()

        return "OK. Will assign %s on join" % (role_name)
    else:
        return "Invalid type."


@hook.event(EventType.join)
def do_join(event, storage, send_message, str_to_id, server):
    if storage["on_join"] == None:
        return

    for item in storage["on_join"]:
        if item["type"] == "message":
            creation_date = datetime.datetime.utcfromtimestamp(
                int((int(event.member.id) >> 22) + 1420070400000) / 1000
            )
            args = {
                "AGE": time_utils.sec_to_human(
                    (datetime.datetime.now() - creation_date).total_seconds()
                ),
                "USER": event.member.name,
                "USER_ID": event.member.id,
            }
            if "{SEEN_CNT}" in item["message"]:
                args["SEEN_CNT"] = get_msg_cnt_for_user(event.member.id)

            message = item["message"].format(**args)
            send_message(target=item["chan"], text=message, timeout=item["timeout"])

        elif item["type"] == "role":
            for role in server.get_roles():
                if role.id == item["role"]:
                    event.member.add_role(role)


@hook.command(permissions=Permission.admin)
def list_join_events(storage, id_to_chan, id_to_role_name, reply):
    """
    List on-join events
    """
    msg = ""
    msgs = []
    roles = []
    cnt = Counter()

    if not "on_join" in storage:
        return "No events set"

    for item in storage["on_join"]:
        if item["type"] == "message":
            msgs.append(item)
        elif item["type"] == "role":
            roles.append(item)

    if len(msgs) == 0 and len(roles) == 0:
        return "No join events set"

    for m in msgs:
        msg += f"""
---
`ID`: {cnt.get()}
`Message:` {m["message"]}
`Channel:` {id_to_chan(m["chan"])}
`Timeout:` {time_utils.sec_to_human(str(m["timeout"]))}"""

        # msg += """\n---\n`Message:` """ + m["message"]
        # msg += "\n`Channel:` " + id_to_chan(m["chan"])
        # if m["timeout"] != 0:
        #    msg += "\n`Timeout:` " + str(m["timeout"])

    if len(roles) > 0:
        msg += "\n---\n`Roles given on join:` \n" + "\n".join(
            "`ID:` %s `Name:` %s" % (str(cnt.get()), id_to_role_name(i["role"]))
            for i in roles
        )

    reply(msg, allowed_mentions=nextcord.AllowedMentions.none())


@hook.command(permissions=Permission.admin)
def get_timeout_for(storage, text, str_to_id):
    """
    Get timeout for a join event
    """
    try:
        e_id = int(text)
    except ValueError:
        return "Please enter an event ID"
    evt = find_event_by_id(storage, e_id)
    if not evt:
        return "Entry not found"

    if evt["type"] == "role":
        return "Found a matching entry but it's a role assignation."

    if evt["timeout"] != 0:
        return "Timeout set to %d" % evt["timeout"]
    else:
        return "No timeout set"


@hook.command(permissions=Permission.admin)
def set_timeout_for(storage, text, str_to_id):
    """
    <join event id, timeout> - Set timeout for a join event. Use '5s' for timeout to set it to 5s or 1m to set it to one minute.
    """
    text = text.rsplit(maxsplit=1)
    try:
        e_id = int(text[0])
    except ValueError:
        return "Please enter an event ID"
    evt = find_event_by_id(storage, text[0])
    if not evt:
        return "Entry not found"

    if evt["type"] == "role":
        return "Found a matching entry but it's a role assignation."

    try:
        evt["timeout"] = time_utils.timeout_to_sec(text[1])
        storage.sync()
        return "Done. Set timeout to %d seconds" % evt["timeout"]
    except:
        import traceback

        traceback.print_exc()

    storage.sync()


@hook.command(permissions=Permission.admin)
def del_join_event(storage, text, str_to_id):
    """
    <event id> - delete a join event
    """
    try:
        e_id = int(text)
    except ValueError:
        return "Please enter an event ID"
    to_delete = find_event_by_id(storage, e_id)
    if not to_delete:
        return "Entry not found"

    storage["on_join"].remove(to_delete)
    storage.sync()

    return "Done"
