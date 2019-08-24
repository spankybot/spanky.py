import datetime
from spanky.utils import time_utils
from plugins.discord_utils import *
from collections import OrderedDict

time_tokens = ['s', 'm', 'h', 'd']
SEC_IN_MIN = 60
SEC_IN_HOUR = SEC_IN_MIN * 60
SEC_IN_DAY = SEC_IN_HOUR * 24

def assign_temp_role(rstorage, server, bot, role, text, command_name, str_to_id, event):
    data = text.split(" ")

    if len(data) < 2:
        return "Needs at least user and time (and reason) (e.g. .{CMD} @plp, 5m - to give @plp {CMD} for 5 minutes OR .{CMD} @plp 5m bad user - to give @plp {CMD} for 5m and save the reason \"bad user\")".format(CMD=command_name), None

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
            if char == 's':
                total_seconds += value
            elif char == 'm':
                total_seconds += value * SEC_IN_MIN
            elif char == 'h':
                total_seconds += value * SEC_IN_HOUR
            elif char == 'd':
                total_seconds += value * SEC_IN_DAY

            last_start = pos + 1

    texp = datetime.datetime.now().timestamp() + total_seconds

    brole = get_role_by_name(server, role)
    member = get_user_by_id(server, user)

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
        reason_entry = add_reason(rstorage, event, member, reason, server, texp, brole.name)

        new_entry = {}
        new_entry["user"] = user
        new_entry["expire"] = texp
        new_entry["crt_roles"] = crt_roles
        new_entry["reason_id"] = reason_entry["Case ID"]

        rstorage[command_name].append(new_entry)
        member.replace_roles([brole])

        rstorage.sync()
        return "Gave <@%s> %s seconds %s time" % (user, str(total_seconds), command_name), reason_entry
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
            reason["Modified by"] = "%s / %s" % (event.author.name, str(event.author.id))
            reason["Modified expire time"] = datetime.datetime.fromtimestamp(new_time).strftime("%H:%M:%S %d-%m-%Y")

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
    new_elem["Expire date"] = datetime.datetime.fromtimestamp(expire).strftime("%H:%M:%S %d-%m-%Y")
    new_elem["Link"] = "https://discordapp.com/channels/%s/%s/%s" % (server.id, event.channel.id, event.msg.id)
    new_elem["Author"] = "%s / %s" % (event.author.name, str(event.author.id))
    new_elem["User"] = "%s / %s" % (user.name, user.id)
    new_elem["Case ID"] = rstorage["case_id"]

    user_lst.append(new_elem)

    rstorage["case_id"] += 1
    rstorage.sync()

    return new_elem

def close_case(text, storage):
    if "reasons" not in storage:
        return "No reasons set"

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

        rtext = "Case: %s | Type: %s | Date: %s | Author: %s" % \
                (reason["Case ID"], rtype, reason["Date"], reason["Author"].split("/")[0])
        rlist.append(rtext)

    return rlist

def get_rtime(text, str_to_id, storage, command_name):
    user = str_to_id(text)

    if user in storage[command_name]:
        tnow = datetime.datetime.now().timestamp()

        tsec_left = storage[command_name][user]['expire'] - tnow

        return "Remaining: " + time.utils.sec_to_human(tsec_left)
    else:
        return "User not in %s list" % command_name


def check_exp_time(rstorage, command_name, role, server):
    if command_name not in rstorage:
        return

    tnow = datetime.datetime.now().timestamp()
    to_del = []

    for elem in rstorage[command_name]:
        if elem['expire'] < tnow:
            to_del.append(elem)

    for elem in to_del:
        role = get_role_by_name(server, role)
        member = get_user_by_id(server, elem["user"])

        new_roles = []
        for role_id in elem['crt_roles']:
            role = get_role_by_id(server, role_id)
            if role:
                new_roles.append(role)

        if member:
            member.replace_roles(new_roles)

        rstorage[command_name].remove(elem)
        rstorage.sync()
