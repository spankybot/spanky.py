from spanky.hook2 import (
    Hook,
    Command,
    ComplexCommand,
    ActionCommand,
    EventType,
    MiddlewareResult,
)

from discord import AllowedMentions
from spanky.utils import discord_utils as dutils

no_mention = AllowedMentions.none()

# TODO: storage might be unsafe?
hook = Hook("cmd_owner_hook", storage_name="plugins_admin.json")


@hook.global_middleware(priority=15)
def check_cmd_owner(action: ActionCommand, hooklet: Command):
    # If not already admin, we should add that he is "technically" an admin for the owner.
    cmd = CmdPerms(hook.server_storage(action.server_id), action.triggered_command)
    print(action.context)
    if "admin" not in action.context["perms"]["creds"]:

        allowed_roles = set(cmd.owners)
        user_roles = set([i.id for i in action.author.roles])
        if user_roles & allowed_roles:
            action.context["perms"]["creds"].append("admin")


@hook.global_middleware(priority=20)
def check_chgroups(action: ActionCommand, hooklet: Command):
    storage = hook.server_storage(action.server_id)
    cmd = CmdPerms(storage, action.triggered_command)
    print(f"DEBUG: Command info: {cmd!s}")
    print(storage)
    print("X", storage["default_bot_chan"], action.channel.id)
    if cmd.customized:
        if cmd.unrestricted:
            return MiddlewareResult.CONTINUE
        if len(cmd.fchannel_ids) > 0 and action.channel.id in cmd.fchannel_ids:
            action.message.delete_message()
            return (
                MiddlewareResult.DENY,
                "Command can't be used in "
                + ", ".join(action._raw.id_to_chan(i) for i in cmd.fchannel_ids),
            )
        if len(cmd.channel_ids) > 0 and action.channel.id not in cmd.channel_ids:
            action.message.delete_message()
            return (
                MiddlewareResult.DENY,
                "Command can't be here. Try using it in "
                + ", ".join(action._raw.id_to_chan(i) for i in cmd.channel_ids),
            )
    elif (
        storage["default_bot_chan"] and action.channel.id != storage["default_bot_chan"]
    ):
        action.message.delete_message()
        return (
            MiddlewareResult.DENY,
            "Command can only be used in "
            + action._raw.id_to_chan(storage["default_bot_chan"]),
        )


class CmdPerms:
    def __init__(self, storage, cmd: str):
        self.storage = storage
        self.cmd: str = cmd

        self.customized: bool = False
        self.unrestricted: bool = False
        self.owners: list[str] = []
        self.chgroups: list[str] = []
        self.channel_ids: list[str] = []
        self.fchgroups: list[str] = []
        self.fchannel_ids: list[str] = []

        if "commands" not in storage:
            storage["commands"] = {}
            storage.sync()

        if cmd not in storage["commands"]:
            storage["commands"][cmd] = {}
            storage.sync()

        if "owner" in storage["commands"][cmd].keys():
            self.owners.extend(storage["commands"][cmd]["owner"])
            if len(self.owners) > 0:
                self.customized = True

        if "groups" in storage["commands"][cmd].keys():
            self.chgroups.extend(storage["commands"][cmd]["groups"])

            for chgroup in storage["commands"][cmd]["groups"]:
                if "channels" in storage["chgroups"][chgroup].keys():
                    self.channel_ids.extend(storage["chgroups"][chgroup]["channels"])
            if len(self.channel_ids) > 0:
                self.customized = True

        if "fgroups" in storage["commands"][cmd].keys():
            self.fchgroups.extend(storage["commands"][cmd]["fgroups"])

            for chgroup in storage["commands"][cmd]["fgroups"]:
                self.fchannel_ids.extend(storage["chgroups"][chgroup]["channels"])
            if len(self.fchannel_ids) > 0:
                self.customized = True

        if (
            "unrestricted" in storage["commands"][cmd].keys()
            and storage["commands"][cmd]["unrestricted"] != False
        ):
            self.unrestricted = True
            self.customized = True

    def __str__(self):
        return f"CmdPerms[restricted={(not self.unrestricted)!s} customized={self.customized!s}]"

    def save(self):
        self.storage["commands"][self.cmd]["owner"] = self.owners
        self.storage["commands"][self.cmd]["unrestricted"] = self.unrestricted
        self.storage["commands"][self.cmd]["groups"] = self.chgroups
        self.storage["commands"][self.cmd]["fgroups"] = self.fchgroups

        self.storage.sync()


admin_master_cmd = ComplexCommand(hook, "admin_config", permissions="admin")


admin_cmd = admin_master_cmd.complex_subcommand("admin_roles")


@admin_cmd.subcommand(name="add")
def admin_add(str_to_id, text, storage, server):
    """Add a new admin role."""
    if "admin_roles" not in storage:
        storage["admin_roles"] = []
        storage.sync()

    drole = dutils.get_role_by_id_or_name(server, text)
    if drole == None:
        return "Not a role. Use either role name or mention the role when running the command"
    if drole.id in storage["admin_roles"]:
        return "Role is already an admin role!"

    storage["admin_roles"].append(drole.id)
    storage.sync()
    return "Role added."


# am schimbat din list in list_roles pentru a nu suprascrie tipul
@admin_cmd.subcommand(name="list")
def admin_list_roles(reply, storage, id_to_role_name):
    """List currently set admin roles."""
    if "admin_roles" not in storage or len(storage["admin_roles"]) == 0:
        return "No admin roles set."
    reply(
        ", ".join([id_to_role_name(id) for id in storage["admin_roles"]]),
        allowed_mentions=no_mention,
    )


@admin_cmd.subcommand(name="remove")
def admin_remove(storage, text, str_to_id):
    """Remove admin role from list."""
    if "admin_roles" not in storage:
        storage["admin_roles"] = []
        storage.sync()

    drole = dutils.get_role_by_id_or_name(server, text)
    if drole == None:
        return "Not a role. Use either role name or mention the role when running the command"
    if drole.id not in storage["admin_roles"]:
        return "Role is not an admin role!"

    if len(storage["admin_roles"]) == 1:
        return (
            "Cannot remove role, because this is the only admin role for this server."
        )

    storage["admin_roles"].remove(drole.id)
    storage.sync()

    return "Done."


chgroups = admin_master_cmd.complex_subcommand("chgroup")


@chgroups.subcommand(name="create", format="chan")
def chgroup_create(storage, text):
    if "chgroups" not in storage:
        storage["chgroups"] = {}
        storage.sync()
    if text in storage["chgroups"].keys():
        return "Channel group already exists!"
    storage["chgroups"][text] = {}
    storage.sync()
    return "Channel group created"


@chgroups.subcommand(name="list")
def chgroup_list(storage):
    if "chgroups" not in storage:
        storage["chgroups"] = {}
        storage.sync()
    if len(storage["chgroups"].keys()) == 0:
        return "No channel groups created"
    return ", ".join("`" + storage["chgroups"].keys() + "`")


@chgroups.subcommand(name="remove", format="chgroup")
def chgroup_remove(storage, text):
    if "chgroups" not in storage:
        storage["chgroups"] = {}
        storage.sync()
    if text not in storage["chgroups"].keys():
        return "Channel group doesn't exist!"
    storage["chgroups"].pop(text)
    storage.sync()
    return "Channel group deleted"


chgroup_chans = admin_master_cmd.complex_subcommand("chgroup_chans")


def check_chgroup(storage, chgname):
    if "chgroups" not in storage:
        storage["chgroups"] = {}
        storage.sync()
    return chgname in storage["chgroups"]


@chgroup_chans.subcommand(name="add", format="chgroup chan")
def chgr_chan_add(storage, text):
    chgname, chan = text.split()
    if not check_chgroup(storage, chgname):
        return "Channel group does not exist"
    chgr = dutils.get_channel_by_id(storage, chan)
    if not chgr:
        return "Channel does not exist"
    if "channels" not in storage["chgroups"][chgname]:
        storage["chgroups"][chgname]["channels"] = []
    storage["chgroups"][chgname]["channels"].append(chgr.id)
    storage.sync()
    return "Done."


@chgroup_chans.subcommand(name="list", format="chgroup")
def chgr_chan_list(storage, text, id_to_chan):
    chgname = text
    if not check_chgroup(storage, chgname):
        return "Channel group does not exist"
    if "channels" not in storage["chgroups"][chgname]:
        storage["chgroups"][chgname]["channels"] = []
        storage.sync()
    vals = storage["chgroups"][chgname]["channels"]
    if len(vals) > 0:
        return ", ".join(id_to_chan(i) for i in vals)
    return "No channels in channel group"


@chgroup_chans.subcommand(name="remove", format="chgroup chan")
def chgr_chan_remove(storage, text, str_to_id):
    chgname, chan = text.split()
    if not check_chgroup(storage, chgname):
        return "Channel group does not exist"
    if "channels" not in storage["chgroups"][chgname]:
        storage["chgroups"][chgname]["channels"] = []
        storage.sync()
    chan = str_to_id(chan)
    if chan not in storage["chgroups"][chgname]["channels"]:
        return "Channel not in channel group"
    storage["chgroups"][chgname]["channels"].remove(chan)
    storage.sync()
    return "Done"


chgroup_cmds = admin_master_cmd.complex_subcommand("chgroup_cmds")


@chgroup_cmds.subcommand(name="add", format="cmd chgroup")
def chgr_cmds_add(storage, text, str_to_id, server):
    cmd, chgname = text.split()
    if not check_chgroup(storage, chgname):
        return "Channel group does not exist"
    cmd = CmdPerms(storage, cmd)
    if chgname in cmd.chgroups:
        return "Channel group already assigned to command!"
    cmd.chgroups.append(chgname)
    cmd.save()
    return "Done."


@chgroup_cmds.subcommand(name="list", format="cmd")
def chgr_cmds_list(storage, text, str_to_id, server):
    cmd = CmdPerms(storage, text)
    if len(cmd.chgroups) == 0:
        return "No channel groups for command"
    return ", ".join(cmd.chgroups)


@chgroup_cmds.subcommand(name="remove", format="cmd chgroup")
def chgr_cmds_remove(storage, text, str_to_id, server):
    cmd, chgname = text.split()
    cmd = CmdPerms(storage, cmd)
    if chgname not in cmd.chgroups:
        return "Channel group not assigned to command!"
    cmd.chgroups.remove(chgname)
    cmd.save()
    return "Done."


fchgroups = admin_master_cmd.complex_subcommand("fchgroups")


@fchgroups.subcommand(name="add", format="cmd fchgroup")
def fchgr_cmds_add(storage, text, server):
    cmd, chgname = text.split()
    if not check_chgroup(storage, chgname):
        return "Channel group does not exist"
    cmd = CmdPerms(storage, cmd)
    if chgname in cmd.fchgroups:
        return "Forbidden channel group already assigned to command!"
    cmd.fchgroups.append(chgname)
    cmd.save()
    return "Done."


@fchgroups.subcommand(name="list", format="cmd")
def fchgr_cmds_list(storage, text, server):
    cmd = CmdPerms(storage, text)
    if len(cmd.fchgroups) == 0:
        return "No forbidden channel groups for command"
    return ", ".join(cmd.fchgroups)


@fchgroups.subcommand(name="remove", format="cmd fchgroup")
def fchgr_cmds_remove(storage, text, server):
    cmd, chgname = text.split()
    cmd = CmdPerms(storage, cmd)
    if chgname not in cmd.fchgroups:
        return "Forbidden channel group not assigned to command!"
    cmd.fchgroups.remove(chgname)
    cmd.save()
    return "Done."


cmd_owners = admin_master_cmd.complex_subcommand("cmd_owner")


@cmd_owners.subcommand(name="add", format="cmd ugroup")
def cmd_owner_add(storage, text, server):
    cmd, ugroup = text.split()
    cmd = CmdPerms(storage, cmd)
    role = dutils.get_role_by_id_or_name(ugroup)
    if not role:
        return "Role doesn't exist."
    if role.id in cmd.owners:
        return "Role already command owner."
    cmd.owners.append(role.id)
    cmd.save()
    return "Done."


@cmd_owners.subcommand(name="list", format="cmd")
def cmd_owner_list(storage, text, server):
    cmd = CmdPerms(storage, text)
    if len(cmd.owners) == 0:
        return "No command owners set."
    return ", ".join(cmd.owners)


@cmd_owners.subcommand(name="remove", format="cmd ugroup")
def cmd_owner_add(storage, text, server, str_to_id):
    cmd, ugroup = text.split()
    cmd = CmdPerms(storage, cmd)
    role = dutils.get_role_by_id_or_name(ugroup)
    if not role:
        role = type("", (), {})
        role.id = str_to_id(text.split()[0])
        return "Role doesn't exist."
    if role.id not in cmd.owners:
        return "Role not command owner."
    cmd.owners.remove(role.id)
    cmd.save()
    return "Done."


bot_channel = admin_master_cmd.complex_subcommand("bot_channel")


@bot_channel.subcommand(name="set", format="channel")
def bot_chan_set(storage, text, server):
    chan = dutils.get_channel_by_id_or_name(server, text)
    if not chan:
        return "Invalid channel."

    storage["default_bot_chan"] = chan.id
    storage.sync()
    return "Done."


@bot_channel.subcommand(name="get")
def bot_chan_get(storage, id_to_chan):
    chan = storage["default_bot_chan"]
    if chan:
        return id_to_chan(chan)
    return "Not set."


@bot_channel.subcommand(name="clear")
def bot_chan_clear(storage, text):
    chan = storage["default_bot_chan"]
    if chan:
        storage["default_bot_chan"] = None
        storage.sync()
        return "Channel cleared."
    return "No channel set."


unrestricted_cmds = admin_master_cmd.complex_subcommand("unrestricted_cmd")


@unrestricted_cmds.subcommand(name="make", format="cmd")
def make_ucmd(text, storage):
    cmd = CmdPerms(storage, text)
    if cmd.unrestricted:
        return "Command already unrestricted!"
    cmd.unrestricted = True
    cmd.save()
    return "Command unrestricted."


@unrestricted_cmds.subcommand(name="check", format="cmd")
def check_ucmd(text, storage):
    cmd = CmdPerms(storage, text)
    if cmd.unrestricted:
        return "Command is unrestricted"
    if cmd.customized:
        return "Command is restricted, but not customized."
    return "Command is restricted"


@unrestricted_cmds.subcommand(name="restore", format="cmd")
def restore_ucmd(text, storage):
    cmd = CmdPerms(storage, text)
    if not cmd.unrestricted:
        return "Command already restricted!"
    cmd.unrestricted = False
    cmd.save()
    return "Command restricted."


def migration_help():
    cmd_migration: dict[str, str] = {
        ".add_channel_group <chgroup>": "chgroup create <chgroup>",
        ".list_channel_groups": "chgroup list",
        ".del_channel_group <chgroup>": "chgroup remove <chgroup>",
        "_6": "",
        ".add_chan_to_chgroup <channel> <chgroup>": "chgroup_chans add <chgroup> <channel>",
        ".list_chans_in_chgroup <chgroup>": "chgroup_chans list <chgroup>",
        ".del_chan_from_chgroup <channel> <chgroup>": "chgroup_chans remove <chgroup> <channel>",
        "_5": "",
        ".add_chgroup_to_cmd <command> <chgroup>": "chgroup_cmds add <cmd> <chgroup>",
        ".list_chgroups_for_cmd <command>": "chgroup_cmds list <cmd>",
        ".del_chgroup_from_cmd <command> <channel-group>": "chgroup_cmds remove <cmd> <chgroup>",
        "_1": "",
        ".add_fchgroup_to_cmd <command> <chgroup>": "",
        ".list_fchgroups_for_cmd <command>": "",
        ".del_fchgroup_from_cmd <command> <chgroup>": "",
        "_2": "",
        ".add_owner_to_cmd <command> <owner_role>": "",
        ".list_owners_for_cmd <command>": "",
        ".del_owner_from_cmd <command> <owner_role>": "",
        "_3": "",
        ".restore_restrictions_for_cmd <cmd>": "unrestricted make <cmd>",
        ".is_cmd_unrestricted <cmd>": "unrestricted check <cmd>",
        ".remove_restrictions_for_cmd <cmd>": "unrestricted restore <cmd>",
        "_4": "",
        ".add_admin_role <role>": "admin_roles add <role>",
        ".get_admin_roles": "admin_roles list",
        ".remove_admin_role <role>": "admin_roles remove <role>",
        "_10": "",
        ".set_default_bot_channel <channel>": "bot_channel set <channel>",
        ".list_default_bot_channel": "bot_channel get",
        ".clear_default_bot_channel": "bot_channel clear",
    }

    txt = "Admin command migration guide:\n"

    for old, new in cmd_migration.items():
        if old[0] == "_":
            txt += "\n"
        else:
            txt += f"`{old}` -> `{'TODO' if new == '' else new}`\n"
    return txt


@admin_master_cmd.subcommand(
    doc="Display which subcommand matches the old administration command"
)
def updated_commands():
    return migration_help()
