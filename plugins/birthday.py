import plugins.paged_content as paged
from spanky.plugin import hook
from datetime import datetime
from spanky.utils.cmdparser import CmdParser
from spanky.plugin.permissions import Permission
import spanky.utils.discord_utils as dutils
import pytz
import discord
from collections import OrderedDict

ro = pytz.timezone('Europe/Bucharest')

debug = False

SERVERS = [
    "648937029433950218",  # CNC test server
    "297483005763780613",  # plp test server
    "287285563118190592",  # Roddit
    "779781184665944104",  # robac
]
ELEVATED_PERMS = [Permission.admin, Permission.bot_owner]

@hook.periodic(10)
def birthday_check(bot, send_message):
    for server in bot.backend.get_servers():
        storage = bot.server_permissions[server.id].get_plugin_storage("plugins_birthday.json")

        if "birthdays" not in storage:
            continue
        
        check_birthdays(server, storage, send_message)

def check_birthdays(server, storage, send_message, force=False):
    global last_time
    
    now = datetime.now()

    try:
        if not last_time:
            last_time = now
    except:
        last_time = now

    if not force:
        if debug:
            if now.minute == last_time.minute:
                return
        else:
            if now.hour == last_time.hour:
                return
   
    # reset last_time
    last_time = now

    ro_now = ro.localize(now)
    if debug:
        hour = ro_now.minute
    else:
        hour = ro_now.hour
    
    update_roles(server, storage, now)
    if hour == 8: # 8am
        send_messages(server, storage, now, send_message)

def update_roles(server, storage, now):
    if "role" not in storage:
        return
    role = server.get_role(storage["role"])
    if not role:
        return
    
    (month, day) = (str(now.month), str(now.day))

    for user in role.members:
        if not is_bday_boy(user.id, storage, now):
            user.remove_role(role)

    if month not in storage["birthdays"]:
        debug_msg(server, storage, "Month not found")
        return
    if day not in storage["birthdays"][month]:
        debug_msg(server, storage, "Day not found")
        return
    for uid in storage["birthdays"][month][day]:
        user = server.get_user(uid)
        if not user:
            debug_msg(server, storage, f"User <@{user.id}> not found.")
            continue
        user.add_role(role)

def send_messages(server, storage, now, send_message):
    if "chan" not in storage:
        debug_msg(server, storage, "Channel not found")
        return
    chan = server.get_chan(storage["chan"])
    if not chan:
        return
    (month, day) = (str(now.month), str(now.day))

    if month not in storage["birthdays"]:
        debug_msg(server, storage, "Month not found")
        return
    if day not in storage["birthdays"][month]:
        debug_msg(server, storage, "Day not found")
        return
    for uid in storage["birthdays"][month][day]:
        user = server.get_user(uid)
        if not user:
            debug_msg(server, storage, f"User <@{user.id}> not found.")
            continue
        msg = storage["bday_message"].replace("<userid>", f"<@{user.id}>")
        try:
            send_message(msg, server=server, target=chan.id, check_old=False, allowed_mentions=discord.AllowedMentions(everyone=False, users=[user._raw], roles=False))
        except Exception as e:
            debug_msg(server, storage, f"Send Message Exception: {str(e)}")
            import traceback
            print(traceback.format_exc())

def debug_msg(server, send_message, msg):
    send_message(f"(Birthday debug) {msg}", server=server, target="449899630176632842", check_old=False)

def get_date():
    date = datetime.today()
    return (date.day, date.month)

def validate_date(day, month):
    try:
        date = datetime(2020, month, day) # 2020 is leap year, so 29 February should count as valid
        return True
    except:
        return False

def parse_day(text):
    try:
        (day, month) = text.split('-')
        if not validate_date(int(day), int(month)):
            raise Exception("Invalid date")
        return (str(int(day)), str(int(month)))
    except:
        raise Exception("Invalid date")

def find_user(uid, storage):
    for month, month_data in storage["birthdays"].items():
        for day, day_data in month_data.items():
            if uid in day_data:
                return (str(day), str(month))
    return None

def is_bday_boy(uid, storage, date: datetime):
    date = (str(date.day), str(date.month))
    if date == find_user(uid, storage):
        return True
    return False

@hook.command(permissions=ELEVATED_PERMS, server_id=SERVERS)
def bday_dbg(text, reply, server, storage):
    # Rectify incorrect keys
    for month, month_data in storage["birthdays"].items():
        for day in month_data.keys():
            storage["birthdays"][month][str(int(day))] = storage["birthdays"][month].pop(day)
        storage["birthdays"][str(int(month))] = storage["birthdays"].pop(month)
    storage.sync()
    return str(storage["birthdays"])

@hook.command(permissions=ELEVATED_PERMS, server_id=SERVERS)
def trigger_check(server, storage, send_message):
    try:
        check_birthdays(server, storage, send_message, check=True)
    except:
        import traceback
        return str(traceback.format_exc())
    return "Done."

@hook.command(permissions=ELEVATED_PERMS, server_id=SERVERS)
def birthday(text, reply, server, storage):
    # TODO: Maybe write a nicer doc?
    """
    Manage birthday announcements.

    See `.birthday help` for more info
    """ 

    defaultBdayMsg = "<userid> La multzean baaaaaa"

    if "birthdays" not in storage:
        storage["birthdays"] = {}
        storage.sync()

    if "bday_message" not in storage:
        storage["bday_message"] = defaultBdayMsg
        storage.sync()

    def bday_list(text):
        msg = f"""INFO:
- Message: `{storage['bday_message']}`
{f"- Channel: <#{storage['chan']}>" if 'chan' in storage else '- No channel set.'}
{f"- Role: <@&{storage['role']}>" if 'role' in storage else '- No role set.'}
All birthdays:

"""
        for month, month_data in OrderedDict(sorted(storage["birthdays"].items())).items():
            for day, day_data in OrderedDict(sorted(month_data.items())).items():
                msg += f"{datetime.now().year}-{month}-{day}:\n"
                users = []
                for idx, user in enumerate(day_data):
                    duser = server.get_user(user)
                    if not duser:
                        del storage["birthdays"][month][day][idx]
                        continue
                    users.append(f"<@{user}>")
                msg += ', '.join(users)
                msg += "\n\n"
        storage.sync()
        reply(msg, allowed_mentions=discord.AllowedMentions.none())

    def bday_set_role(text):
        id = dutils.str_to_id(text[0])
        role = server.get_role(id)
        if not role:
            reply("Invalid role.")
            return

        storage["role"] = id
        storage.sync()
        reply("Set role.")

    def bday_del_role(text):
        if "role" not in storage:
            reply("No role set.")
            return

        del storage["role"]
        storage.sync()
        reply("Role unset.")

    def bday_set_channel(text):
        id = dutils.str_to_id(text[0])
        channel = server.get_chan(id)
        if not channel:
            reply("Invalid channel.")
            return

        storage["chan"] = id
        storage.sync()
        reply("Set channel.")

    def bday_del_channel(text):
        if "chan" not in storage:
            reply("No channel set.")
            return

        del storage["chan"]
        storage.sync()
        reply("Channel unset.")
    
    def bday_add(text):
        user = server.get_user(dutils.str_to_id(text[0]))
        if not user:
            reply("Invalid user.")
            return

        try:
            date = parse_day(text[1])
        except Exception as e:
            reply(str(e))
            return
        
        if find_user(user.id, storage):
            reply("User already has a birthday set, remove him first!")
            return
        
        if date[1] not in storage["birthdays"]:
            storage["birthdays"][date[1]] = {}

        if date[0] not in storage["birthdays"][date[1]]:
            storage["birthdays"][date[1]][date[0]] = [] 

        storage["birthdays"][date[1]][date[0]].append(user.id)
        storage.sync()

        reply("Added birthday.")
    
    def bday_remove(text):
        user = server.get_user(dutils.str_to_id(text[0]))
        if not user:
            reply("Invalid user.")
            return

        date = find_user(user.id, storage)
        if not date:
            reply("User does not have a birthday set.")
            return

        storage["birthdays"][date[1]][date[0]].remove(user.id)
        if len(storage["birthdays"][date[1]][date[0]]) == 0:
            del storage["birthdays"][date[1]][date[0]]

        if len(storage["birthdays"][date[1]]) == 0:
            del storage["birthdays"][date[1]]

        storage.sync()
        reply("Removed birthday.")

    def bday_setDate(text):
        user = server.get_user(dutils.str_to_id(text[0]))
        if not user:
            reply("Invalid user.")
            return

        date = find_user(user.id, storage)
        if not date:
            reply("User does not have a birthday set.")
            return

        try:
            new_date = parse_day(text[1])
        except Exception as e:
            reply(str(e))
            return

        if date == new_date:
            reply("User already has this birthday set!")
            return

        storage["birthdays"][date[1]][date[0]].remove(user.id)
        if len(storage["birthdays"][date[1]][date[0]]) == 0:
            del storage["birthdays"][date[1]][date[0]]

        if len(storage["birthdays"][date[1]]) == 0:
            del storage["birthdays"][date[1]]

        if new_date[1] not in storage["birthdays"]:
            storage["birthdays"][new_date[1]] = {}

        if new_date[0] not in storage["birthdays"][new_date[1]]:
            storage["birthdays"][new_date[1]][new_date[0]] = [] 
        
        storage["birthdays"][new_date[1]][new_date[0]].append(user.id)
        storage.sync()

        reply("Updated birthday date.")
    
    def bday_setMessage(text):
        if len(text) == 0:
            text = [defaultTopMsg]
        storage["bday_message"] = ' '.join(text) 
        reply(f'Updated birthday message to "{" ".join(text)}"')

    parser = CmdParser(
        "birthday",
        "Manage birthdays",
        args=[
            CmdParser(
                "command",
                "birthday command",
                options=[
                    CmdParser(
                        "list",
                        "List birthdays",
                        action=bday_list),
                    CmdParser(
                        "add",
                        "Add birthday",
                        args=[CmdParser(
                            "user",
                            "User to celebrate",
                            required=True),
                            CmdParser(
                            "bday",
                            "Birthday date (format: DD-MM)",
                            required=True
                            )],
                        action=bday_add),
                    CmdParser(
                        "updateMessage",
                        "Update birthday message",
                        args=[CmdParser(
                            "user",
                            "User to update",
                            required=True),
                            CmdParser(
                            "message",
                            "Birthday message. Use <userid> for the mention",
                            required=False)],
                        action=bday_setMessage),
                    CmdParser(
                        "updateDate",
                        "Update birthday date",
                        args=[CmdParser(
                            "user",
                            "User to update",
                            required=True),
                            CmdParser(
                            "date",
                            "Birthday date (format: DD-MM)",
                            required=True)],
                        action=bday_setDate),
                    CmdParser(
                        "remove",
                        "Remove birthday",
                        args=[CmdParser(
                            "user",
                            "User to remove birthday",
                            required=True)],
                        action=bday_remove),
                    CmdParser(
                        "setRole",
                        "Set birthday role",
                        args=[CmdParser(
                            "role",
                            "Role to set",
                            required=True)],
                        action=bday_set_role),
                    CmdParser(
                        "delRole",
                        "Unset birthday role",
                        action=bday_del_role),
                    CmdParser(
                        "setChan",
                        "Set birthday message channel",
                        args=[CmdParser(
                            "chan",
                            "Channel to send messages in",
                            required=True)],
                        action=bday_set_channel),
                    CmdParser(
                        "delChan",
                        "Unset birthday message channel",
                        action=bday_del_channel
                    ),
                ]
            )
        ]
    )

    try:
        parser.parse(text)
    except CmdParser.HelpException as e:
        return "```\n" + str(e) + "\n```"
    except CmdParser.Exception as e:
        return "```\n" + str(e) + "\n```"

