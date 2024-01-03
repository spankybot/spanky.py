import os
import datetime
import spanky.utils.discord_utils as dutils
import plugins.paged_content as paged
import io
import nextcord
import csv
from spanky.hook2 import Hook, Command, ComplexCommand

from spanky.utils import time_utils
from collections import OrderedDict
from spanky.plugin.permissions import Permission
from spanky.hook2 import Hook, EventType, Command

hook = Hook("temp_role", storage_name="plugins_temp_role")

time_tokens = ["s", "m", "h", "d"]
SEC_IN_MIN = 60
SEC_IN_HOUR = SEC_IN_MIN * 60
SEC_IN_DAY = SEC_IN_HOUR * 24


def log_action(storage, ret_val, send_embed, title):
    # If the command is set to log the action onto a channel
    if "modlog_chan" in storage:
        # Compose the reply
        log_text = ""
        for k, v in ret_val.items():
            log_text += "**%s:** %s\n" % (k, v)

        # Send it as embed
        send_embed(title, "", {"Details": log_text}, target=storage["modlog_chan"])


def register_cmd(cmd, server):
    """
    Register a user defined command
    """

    cmd_name = cmd["name"]

    def do_cmd(text, server, storage, event, send_embed):
        """
        Temporary role assignment command as defined by server ops.
        """
        print("Got temp cmd %s" % cmd_name)
        if "cmd_type" not in storage["cmds"][cmd_name]:
            storage["cmds"][cmd_name]["cmd_type"] = "temporary"
            storage.sync()

        ret_val = None
        if storage["cmds"][cmd_name]["cmd_type"] == "temporary":
            ret_val = give_temp_role(text, server, cmd_name, storage, event)
        elif storage["cmds"][cmd_name]["cmd_type"] == "toggled":
            ret_val = give_toggled_role(text, server, cmd_name, storage, event)
        else:
            return "Unknown command type"

        if type(ret_val) == str:
            return ret_val

        # Log the action
        log_action(
            storage,
            ret_val,
            send_embed,
            "User given the `%s` role" % storage["cmds"][cmd_name]["role_name"],
        )

        return "Done."

    hook.add_command(
        Command(hook, cmd_name, do_cmd, server_id=server.id, permissions="admin")
    )


@hook.event(EventType.on_conn_ready)
def init_cmds(bot, storage_getter):
    """
    Register all commands on bot ready
    """

    for server in bot.backend.get_servers():
        storage = storage_getter(server.id)

        if "cmds" not in storage:
            continue

        for cmd in storage["cmds"]:
            print("[%s] Registering %s" % (server.id, cmd))
            register_cmd(storage["cmds"][cmd], server)


@hook.command(permissions=Permission.admin)
def create_temp_role_cmd(text, hook, str_to_id, server, bot, storage):
    """
    <command name, role> - create a command that assigns a temporary role by specifying `command_name role`
    """

    text = text.split()

    # Check if length is correct
    if len(text) < 2:
        return create_temp_role_cmd.__doc__

    cmd = text[0]

    # Check minumum length
    if len(cmd) < 5:
        return "Command length needs to be at least 5."

    # Check that command exists

    if hook.root.get_command(cmd) != None:
        return "Command `%s` already exists. Try using another name." % cmd

    # Get the given role
    role = dutils.get_role_by_id(server, str_to_id(text[1]))
    if not role:
        role = dutils.get_role_by_name(server, text[1])

    if not role:
        return "No such role " + text[1]

    if "cmds" not in storage:
        storage["cmds"] = {}

    # Create new object
    new_cmd = {}
    new_cmd["cmd_type"] = "temporary"
    new_cmd["name"] = cmd
    new_cmd["role_id"] = role.id
    new_cmd["role_name"] = role.name

    storage["cmds"][cmd] = new_cmd
    storage.sync()

    register_cmd(new_cmd, server)

    return "Done"


@hook.command(permissions=Permission.admin)
def list_temp_role_cmds(storage):
    """
    list temporary role commands
    """
    if "cmds" not in storage:
        return "No commands created"
    else:
        return ", ".join("`%s`" % cmd["name"] for cmd in storage["cmds"].values())


@hook.command(permissions=Permission.admin)
def delete_temp_role_cmd(storage, text, hook):
    """
    <command_name> - delete a temporary role command
    """
    if "cmds" not in storage:
        return "No commands created"

    for cmd in storage["cmds"].values():
        if cmd["name"] == text:
            # Remove plugin entry from the hook and globals
            hook.remove_command(cmd["name"])
            del storage["cmds"][cmd["name"]]

            storage.sync()

            return "Done"

    return "Command not registered"


@hook.command(permissions=Permission.admin)
def set_temp_role_cmd_type(storage, text):
    if "cmds" not in storage:
        return "No commands created"
    text = text.split()
    if len(text) != 2:
        return "Invalid arguments"
    if not (text[1] == "temporary" or text[1] == "toggled"):
        return "Invalid command type"

    for cmd in storage["cmds"].values():
        if cmd["name"] == text[0]:
            storage["cmds"][cmd["name"]]["cmd_type"] = text[1]
            storage.sync()
            return "Done"
    return "Command not registered"


@hook.command(permissions=Permission.admin)
async def userhistory(text, storage, async_send_message, server):
    """<user> - List confinement reasons for user"""

    def get_reasons(text, storage, user_id):
        if "reasons" not in storage:
            return ["No reasons set"]

        if user_id not in storage["reasons"]:
            return ["No history for given user"]

        rlist = []
        for reason in storage["reasons"][user_id]:
            rtype = "No type given"

            # Skip closed cases
            if "Closed" in reason and reason["Closed"]:
                continue

            # Type may be missing
            if "Type" in reason:
                rtype = reason["Type"]

            rtext = "Case: %s | Type: %s | Date: %s | Author: %s" % (
                reason["Case ID"],
                rtype,
                reason["Date"],
                reason["Author"].split("/")[0],
            )
            rlist.append(rtext)

        return rlist

    try:
        # Get the user
        user_id = dutils.str_to_id(text)

        # Get reasons
        usr_hist = get_reasons(text, storage, user_id)

        # Print as pages
        paged_content = paged.element(
            usr_hist, async_send_message, "User history:", no_timeout=True
        )
        await paged_content.get_crt_page()
    except:
        import traceback

        traceback.print_exc()


@hook.command(permissions=Permission.admin)
def close_user_case(text, storage):
    """
    <id> - mark user case as closed
    """
    if "reasons" not in storage:
        return "No user cases set"

    try:
        case_id = int(text)
    except:
        return "%s is not a number. I need a number to identify a case ID." % text

    for user_id in storage["reasons"]:
        for reason in storage["reasons"][user_id]:
            if reason["Case ID"] == case_id:
                if "Closed" in reason and reason["Closed"]:
                    return "Case already closed."
                reason["Closed"] = True
                storage.sync()
                return "Done"

    return "Case ID %d not found" % case_id


@hook.command(permissions=Permission.admin)
def show_user_case(text, storage, send_embed):
    """
    <id> - show details for a given user case
    """
    if "reasons" not in storage:
        return "No user cases set"

    try:
        case_id = int(text)
    except:
        return "%s is not a number. I need a number to identify a case ID." % text

    for user_id in storage["reasons"]:
        for reason in storage["reasons"][user_id]:
            if reason["Case ID"] == case_id:
                # Compose the reply
                log_text = ""
                for k, v in reason.items():
                    log_text += "**%s:** %s\n" % (k, v)

                # Send it as embed
                send_embed("Result", "", {"Details": log_text})


def give_toggled_role(text, server, command_name, storage, event):
    try:
        text = " ".join(text.split()).split()

        if len(text) < 1:
            return 'Needs a user (e.g. .{CMD} @cnc - to toggle @cnc the {CMD} role OR .{CMD} @cnc bad boy - to toggle @cnc the {CMD} role and save the reason "bad boy"'.format(
                CMD=command_name
            )
        user = dutils.get_user_by_id(server, dutils.str_to_id(text[0]))
        if not user:
            return "No such user"

        reason = "Not given"
        if len(text) >= 2:
            reason = " ".join(text[1:])

        # Get the role
        main_role = dutils.get_role_by_id(
            server, storage["cmds"][command_name]["role_id"]
        )

        if main_role is None:
            return "Could not find given role"

        # Check if user is already in toggled role
        present = False
        for role in user.roles:
            if role == main_role:
                present = True
                break

        if not present:
            user.add_role(main_role)

            storage.sync()

            user.send_pm(
                "You have been given the `%s` role.\nReason: %s\nAuthor: %s"
                % (
                    storage["cmds"][command_name]["role_name"],
                    reason,
                    event.author.name,
                )
            )

            return "Given role"
        else:
            user.remove_role(main_role)
            user.send_pm(
                "You have been removed the `%s` role.\nReason: %s\nAuthor: %s"
                % (
                    storage["cmds"][command_name]["role_name"],
                    reason,
                    event.author.name,
                )
            )
            return "Removed the role"

        return "Nothing happened"
    except Exception as e:
        return "Couldn't give role: %s" % repr(e)


def give_temp_role(text, server, command_name, storage, event):
    # Remove extra whitespace and split
    text = " ".join(text.split()).split()

    if len(text) < 2:
        return (
            'Needs at least user and time (e.g. .{CMD} @plp, 5m - to give @plp {CMD} for 5 minutes OR .{CMD} @plp 5m bad user - to give @plp {CMD} for 5m and save the reason "bad user")'.format(
                CMD=command_name
            )
            + "The abbrebiations are: s - seconds, m - minutes, h - hours, d - days."
        )

    # Get user
    user = dutils.get_user_by_id(server, dutils.str_to_id(text[0]))
    if not user:
        return "No such user"

    # Get reason
    reason = "Not given"
    if len(text) >= 3:
        reason = " ".join(text[2:])

    # Get timeout
    timeout_sec = time_utils.timeout_to_sec(text[1])
    # If timeout is 0, double check the input
    if timeout_sec == 0 and text[1] != "0s":
        return (
            "There may have been a problem parsing `%s`. Please check it and run the command again."
            % text[1]
        )

    # When the timeout will expire
    texp = datetime.datetime.now().timestamp() + timeout_sec

    # Get the role
    role = dutils.get_role_by_id(server, storage["cmds"][command_name]["role_id"])

    if role is None:
        return "Could not find given role"

    if "temp_roles" not in storage:
        storage["temp_roles"] = {}

    if command_name not in storage["temp_roles"]:
        storage["temp_roles"][command_name] = []

    # Check if user is already in temp role
    extra = False
    for entry in storage["temp_roles"][command_name]:
        if entry["user_id"] == user.id:
            extra = True
            break

    crt_roles = []
    # Get current roles
    for urole in user.roles:
        # If the role has already been given, assume that it will be timed from now
        if urole.id == role.id:
            continue
        crt_roles.append(urole.id)

    # Check if it's extra time
    if not extra:
        # Create a new user entry
        reason_entry = create_user_reason(
            storage,
            user,
            event.author,
            reason,
            "https://discordapp.com/channels/%s/%s/%s"
            % (server.id, event.channel.id, event.msg.id),
            texp,
            command_name,
        )

        # Create command entry
        new_entry = {}
        new_entry["user_id"] = str(user.id)
        new_entry["user_name"] = user.name
        new_entry["expire"] = texp
        new_entry["crt_roles"] = crt_roles
        new_entry["reason_id"] = reason_entry["Case ID"]

        storage["temp_roles"][command_name].append(new_entry)

        # Replace user roles
        user.replace_roles([role])

        storage.sync()

        user.send_pm(
            "You have been given the `%s` role. It will last for %s.\nReason: %s\nAuthor: %s"
            % (
                storage["cmds"][command_name]["role_name"],
                text[1],
                reason,
                event.author.name,
            )
        )

        return reason_entry

    else:
        adjust_user_reason(
            storage,
            event.author,
            user.id,
            command_name,
            texp,
            "https://discordapp.com/channels/%s/%s/%s"
            % (server.id, event.channel.id, event.msg.id),
        )

        return "Adjusted time for user to %d" % timeout_sec

    return "Nothing happened"


@hook.command(permissions=Permission.admin)
def set_mod_log_chan(server, storage, text):
    """
    <channel> - Set channel for moderator actions. When a moderator action will be done through the bot, details about the action will be logged to this channel.
    """
    channel = dutils.get_channel_by_id(server, dutils.str_to_id(text))

    if not channel:
        return "No such channel"
    else:
        storage["modlog_chan"] = channel.id
        storage.sync()

    return "Done."


@hook.command(permissions=Permission.admin)
def get_mod_log_chan(storage):
    """
    Return the moderator actions channel
    """
    if "modlog_chan" in storage:
        return "<#%s>" % storage["modlog_chan"]
    else:
        return "Channel not set"


@hook.command(permissions=Permission.admin)
def clear_mod_log_chan(storage):
    """
    Clear the moderator actions channel. No moderator actions messages will be sent.
    """
    if "modlog_chan" in storage:
        del storage["modlog_chan"]
        storage.sync()
        return "Done."
    else:
        return "Channel not set"


@hook.command(permissions=Permission.admin)
def warn(user_id_to_object, str_to_id, text, storage, event, send_embed, server):
    """
    <user reason> - Warn a user
    """
    text = text.split(maxsplit=1)
    user = user_id_to_object(str_to_id(text[0]))

    if len(text) < 2:
        return "Warning also needs a reason. Run the command as `.warn @user reason`"

    reason = text[1]

    if user is None:
        return "User not found."

    user_entry = create_user_reason(
        storage,
        user,
        event.author,
        reason,
        "https://discordapp.com/channels/%s/%s/%s"
        % (server.id, event.channel.id, event.msg.id),
        None,
        "Warning",
    )

    # Log the action
    log_action(storage, user_entry, send_embed, "User warned")


@hook.command(permissions=Permission.admin)
def kick(
    user_id_to_object, str_to_id, text, storage, event, send_embed, server, send_pm
):
    """
    <user [reason]> - Kick someone with an optional reason
    """
    text = text.split(maxsplit=1)
    if len(text) == 0:
        return kick.__doc__

    user = user_id_to_object(str_to_id(text[0]))

    reason = "Not given"
    if len(text) > 1:
        reason = text[1]

    if user is None:
        return "User not found."

    user_entry = create_user_reason(
        storage,
        user,
        event.author,
        reason,
        "https://discordapp.com/channels/%s/%s/%s"
        % (server.id, event.channel.id, event.msg.id),
        None,
        "Kick",
    )

    # Log the action
    log_action(storage, user_entry, send_embed, "User kicked")

    details = "\nAuthor: %s" % event.author.name
    if reason:
        details += "\nReason: %s" % reason
    send_pm(
        text="You have been kicked from %s.\n%s" % (server.name, details), user=user
    )

    user.kick()
    return "Okay."


@hook.command(permissions=Permission.admin)
def ban(
    user_id_to_object, str_to_id, text, storage, event, send_embed, server, send_pm
):
    """
    <user [,time], reason> - ban someone permanently or for a given amount of time (e.g. `.ban @plp 5m` bans plp for 5 minutes).
    """
    text = text.split()
    if len(text) == 0:
        return ban.__doc__

    user = user_id_to_object(str_to_id(text[0]))

    # Check for valid user
    if user is None:
        return "User not found."

    texp = None
    timeout_sec = None
    permanent = True
    reason = "Not given"
    # Check if there's a timeout
    if len(text) > 1:
        try:
            timeout_sec = time_utils.timeout_to_sec(text[1])
        except:
            timeout_sec = 0

        # If there's no timeout, then the reason follows the username
        if timeout_sec == 0:
            reason = " ".join(text[1:])
        else:
            permanent = False
            if len(text) > 2:
                reason = " ".join(text[2:])

        texp = timeout_sec + datetime.datetime.now().timestamp()

    user_entry = create_user_reason(
        storage,
        user,
        event.author,
        reason,
        "https://discordapp.com/channels/%s/%s/%s"
        % (server.id, event.channel.id, event.msg.id),
        texp,
        "Ban" if permanent else "Temporary ban",
    )

    # Log the action
    log_action(storage, user_entry, send_embed, "User banned")

    # Create command entry
    new_entry = {}
    new_entry["user_id"] = str(user.id)
    new_entry["user_name"] = user.name
    new_entry["expire"] = texp
    new_entry["reason_id"] = user_entry["Case ID"]

    details = "\nAuthor: %s" % event.author.name
    if reason:
        details += "\nReason: %s" % reason

    if not permanent:
        if "temp_bans" not in storage:
            storage["temp_bans"] = []

        storage["temp_bans"].append(new_entry)
        send_pm(
            text="You have temporarily banned from %s. The ban will last for %s.\n%s"
            % (server.name, text[1], details),
            user=user,
        )
    else:
        send_pm(
            text="You have been permanently banned from %s.\n%s"
            % (server.name, details),
            user=user,
        )
    storage.sync()

    user.ban(server)
    return "User banned permanently." if permanent else "User banned temporarily."


def check_expired_roles(server, storage):
    tnow = datetime.datetime.now().timestamp()
    # Go through each command
    for cmd_name, cmd_list in storage["temp_roles"].items():
        # Go through each element in the command
        for cmd_element in cmd_list:
            to_del = []
            # If timeout has expired
            if cmd_element["expire"] < tnow:
                # Make a list of elements to remove
                to_del.append(cmd_element)

            # For each element replace the roles
            for elem in to_del:
                member = dutils.get_user_by_id(server, elem["user_id"])

                new_roles = []
                for role_id in elem["crt_roles"]:
                    role = dutils.get_role_by_id(server, role_id)
                    if role:
                        new_roles.append(role)

                if member:
                    member.replace_roles(new_roles)

                storage["temp_roles"][cmd_name].remove(elem)
                storage.sync()


async def check_expired_bans(server, storage):
    tnow = datetime.datetime.now().timestamp()
    for elem in storage["temp_bans"]:
        if elem["expire"] == None:
            storage["temp_bans"].remove(elem)
            storage.sync()
        if elem["expire"] < tnow:
            for user in await server.get_bans():
                if elem["user_id"] == str(user.id):
                    user.unban(server)

            storage["temp_bans"].remove(elem)
            storage.sync()


@hook.periodic(1)
async def check_expired_time(bot, storage_getter):
    # Check timeouts for each server
    for server in bot.backend.get_servers():
        storage = storage_getter(server.id)

        if "temp_roles" in storage:
            check_expired_roles(server, storage)

        if "temp_bans" in storage:
            try:
                await check_expired_bans(server, storage)
            except:
                import traceback

                print(traceback.format_exc())


def adjust_user_reason(rstorage, author, user_id, command_name, new_time, message_link):
    reason_id = None
    reason = None
    for entry in rstorage["temp_roles"][command_name]:
        if entry["user_id"] == user_id:
            entry["expire"] = new_time
            reason_id = entry["reason_id"]

    for reason in rstorage["reasons"][user_id]:
        if reason["Case ID"] == reason_id:
            reason["Modified by"] = "%s / %s" % (author.name, str(author.id))
            reason["Modified expire time"] = message_link

    rstorage.sync()
    return reason


def create_user_reason(
    storage, user, author, reason, message_link, expire, reason_type
):
    # Add 'reasons' key
    if "reasons" not in storage:
        storage["reasons"] = {}

    # Set case ID to 0 if not set
    if "case_id" not in storage:
        storage["case_id"] = 0

    # Add user ID as list
    if user.id not in storage["reasons"]:
        storage["reasons"][str(user.id)] = []

    user_lst = storage["reasons"][str(user.id)]

    # Create new element
    new_elem = OrderedDict()
    new_elem["Type"] = reason_type
    new_elem["Case ID"] = storage["case_id"]
    new_elem["Reason"] = reason
    new_elem["Date"] = datetime.datetime.now().strftime("%H:%M:%S %d-%m-%Y")
    if expire:
        new_elem["Expire date"] = datetime.datetime.fromtimestamp(expire).strftime(
            "%H:%M:%S %d-%m-%Y"
        )
    new_elem["Link"] = message_link
    new_elem["Author"] = "%s / %s" % (author.name, str(author.id))
    new_elem["User"] = "%s / %s" % (user.name, str(user.id))
    new_elem["Case ID"] = storage["case_id"]

    user_lst.append(new_elem)

    storage["case_id"] += 1
    storage.sync()

    return new_elem


@hook.command(permissions=Permission.admin)
async def export_cases(storage, event, reply):
    try:
        out_file = io.StringIO(newline="")
        field_names = [
            "Case ID",
            "Type",
            "Reason",
            "Date",
            "Expire date",
            "Link",
            "User",
            "Author",
        ]
        writer = csv.DictWriter(out_file, field_names, extrasaction="ignore")
        writer.writeheader()

        all_reasons = []
        if "reasons" in storage:
            for user in storage["reasons"].values():
                for reason in user:
                    all_reasons.append(reason)

        all_reasons.sort(key=lambda x: x["Case ID"])
        for reason in all_reasons:
            writer.writerow(reason)

        await event.channel.async_send_file(
            nextcord.File(
                fp=io.BytesIO(out_file.getvalue().encode("utf-8")), filename="data.csv"
            )
        )
    except Exception as e:
        reply("Couldn't export cases: %s" % repr(e))


def assign_temp_role(rstorage, server, bot, role, text, command_name, str_to_id, event):
    data = text.split(" ")

    if len(data) < 2:
        return (
            'Needs at least user and time (and reason) (e.g. .{CMD} @plp, 5m - to give @plp {CMD} for 5 minutes OR .{CMD} @plp 5m bad user - to give @plp {CMD} for 5m and save the reason "bad user")'.format(
                CMD=command_name
            ),
            None,
        )

    reason = "Not given"
    if len(data) >= 3:
        reason = " ".join(data[2:])

    user = str_to_id(data[0])
    stime = data[1]

    total_seconds = 0

    last_start = 0
    for pos, char in enumerate(stime):
        if char in time_tokens:
            value = int(stime[last_start:pos])
            if char == "s":
                total_seconds += value
            elif char == "m":
                total_seconds += value * SEC_IN_MIN
            elif char == "h":
                total_seconds += value * SEC_IN_HOUR
            elif char == "d":
                total_seconds += value * SEC_IN_DAY

            last_start = pos + 1

    texp = datetime.datetime.now().timestamp() + total_seconds

    brole = dutils.get_role_by_name(server, role)
    member = dutils.get_user_by_id(server, user)

    if brole == None or member == None:
        print("Internal error " + str(brole) + str(member))
        return "Internal error.", None

    extra = False
    crt_roles = []

    if user in rstorage:
        extra = True

    for role in member.roles:
        #        if brole.id == role.id:
        #            extra = True
        #            break
        crt_roles.append(role.id)

    if command_name not in rstorage:
        rstorage[command_name] = []

    for entry in rstorage[command_name]:
        if entry["user"] == user:
            extra = True
            break

    if not extra:
        reason_entry = add_reason(
            rstorage, event, member, reason, server, texp, brole.name
        )

        new_entry = {}
        new_entry["user"] = user
        new_entry["expire"] = texp
        new_entry["crt_roles"] = crt_roles
        new_entry["reason_id"] = reason_entry["Case ID"]

        rstorage[command_name].append(new_entry)
        member.replace_roles([brole])

        rstorage.sync()
        return (
            "Gave <@%s> %s seconds %s time" % (user, str(total_seconds), command_name),
            reason_entry,
        )
    else:
        reason_entry = adjust_time(rstorage, event, user, command_name, texp)
        return "Adjusted time for user to %d" % total_seconds, reason_entry

    return "wat"


def adjust_time(rstorage, event, user_id, command_name, new_time):
    reason_id = None
    reason = None
    for entry in rstorage[command_name]:
        if entry["user"] == user_id:
            entry["expire"] = new_time
            reason_id = entry["reason_id"]

    for reason in rstorage["reasons"][user_id]:
        if reason["Case ID"] == reason_id:
            reason["Modified by"] = "%s / %s" % (
                event.author.name,
                str(event.author.id),
            )
            reason["Modified expire time"] = datetime.datetime.fromtimestamp(
                new_time
            ).strftime("%H:%M:%S %d-%m-%Y")

    rstorage.sync()
    return reason


def add_reason(rstorage, event, user, reason, server, expire, rtype):
    if "reasons" not in rstorage:
        rstorage["reasons"] = OrderedDict()

    if "case_id" not in rstorage:
        rstorage["case_id"] = 0

    if user.id not in rstorage["reasons"]:
        rstorage["reasons"][user.id] = []

    user_lst = rstorage["reasons"][user.id]

    new_elem = OrderedDict()
    new_elem["Type"] = rtype
    new_elem["Case ID"] = rstorage["case_id"]
    new_elem["Reason"] = reason
    new_elem["Date"] = datetime.datetime.now().strftime("%H:%M:%S %d-%m-%Y")
    new_elem["Expire date"] = datetime.datetime.fromtimestamp(expire).strftime(
        "%H:%M:%S %d-%m-%Y"
    )
    new_elem["Link"] = "https://discordapp.com/channels/%s/%s/%s" % (
        server.id,
        event.channel.id,
        event.msg.id,
    )
    new_elem["Author"] = "%s / %s" % (event.author.name, str(event.author.id))
    new_elem["User"] = "%s / %s" % (user.name, user.id)
    new_elem["Case ID"] = rstorage["case_id"]

    user_lst.append(new_elem)

    rstorage["case_id"] += 1
    rstorage.sync()

    return new_elem


def get_reasons(text, str_to_id, storage):
    if "reasons" not in storage:
        return "No reasons set"

    user_id = str_to_id(text)

    if user_id not in storage["reasons"]:
        return "No history for given user"

    rlist = []
    for reason in storage["reasons"][user_id]:
        rtype = "No type given"

        # Skip closed cases
        if "Closed" in reason and reason["Closed"]:
            continue

        # Type may be missing
        if "Type" in reason:
            rtype = reason["Type"]

        rtext = "Case: %s | Type: %s | Date: %s | Author: %s" % (
            reason["Case ID"],
            rtype,
            reason["Date"],
            reason["Author"].split("/")[0],
        )
        rlist.append(rtext)

    return rlist


def check_exp_time(rstorage, command_name, role, server):
    if command_name not in rstorage:
        return

    tnow = datetime.datetime.now().timestamp()
    to_del = []

    for elem in rstorage[command_name]:
        if elem["expire"] < tnow:
            to_del.append(elem)

    for elem in to_del:
        role = dutils.get_role_by_name(server, role)
        member = dutils.get_user_by_id(server, elem["user"])

        new_roles = []
        for role_id in elem["crt_roles"]:
            role = dutils.get_role_by_id(server, role_id)
            if role:
                new_roles.append(role)

        if member:
            member.replace_roles(new_roles)

        rstorage[command_name].remove(elem)
        rstorage.sync()


###
# Timeout
###
@hook.command(permissions=Permission.admin)
async def timeout(text, server, storage, event, send_embed):
    """
    Timeout an user:
    timeout @plp 1m - timeouts plp for one minute
    timeout @plp - displays timeout for plp
    If the user is timeouted, the timeout can be modified by issuing the timeout command again.
    """
    text = text.split(" ")
    if len(text) == 0:
        return "Please specify a parameter:\n" + timeout.__doc__

    user = dutils.get_user_by_id(server, dutils.str_to_id(text[0]))
    if not user:
        return "Could not find user"

    crt_timeout = user.timeout
    # User info needed
    if len(text) == 1:
        if crt_timeout == None:
            return "User does not have a timeout set."
        else:
            return f"Timeout will expire in: {time_utils.sec_to_human(crt_timeout.timestamp() - time_utils.tnow())}"

    # Set a timeout
    elif len(text) >= 2:
        tosec = time_utils.timeout_to_sec(text[1])
        texp = time_utils.tnow() + tosec

        reason = "Not given"
        if len(text) >= 3:
            reason = " ".join(text[2:])

        await user.set_timeout(time_utils.time_to_date(texp))

        if crt_timeout != None:
            return f"Adjusted timeout to {time_utils.sec_to_human(tosec)}"
        else:
            # Create reason
            reason = add_reason(storage, event, user, reason, server, texp, "timeout")

            # Log the action
            log_action(
                storage,
                reason,
                send_embed,
                "User given timeout",
            )

            return f"Set timeout to {time_utils.sec_to_human(tosec)}"
