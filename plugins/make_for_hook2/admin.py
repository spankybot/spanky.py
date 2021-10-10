import os

from spanky.plugin import hook, permissions
from spanky.plugin.permissions import Permission
from spanky.utils.setclearfactory import (
    SetClearFactory,
    data_type_string,
    data_type_dynamic,
    data_type_list,
)

chgroups = {}
channels_in_chgroups = {}
cgroups_own_cmds = {}
cgroups_forbid_cmds = {}
ugroups_own_cmds = {}
free_to_use_cmds = {}


class CmdPerms:
    def __init__(self, storage, cmd):
        self.cmd = cmd

        self.is_customized = False
        self.owners_ids = []
        self.chgroups = []
        self.channel_ids = []
        self.forbid_chgroups = []
        self.forbid_channel_ids = []

        if not storage["commands"]:
            return

        if cmd in storage["commands"]:
            self.is_customized = True
        else:
            return

        if "owner" in storage["commands"][cmd].keys():
            self.owners_ids.extend(storage["commands"][cmd]["owner"])

        if "groups" in storage["commands"][cmd].keys():
            self.chgroups.extend(storage["commands"][cmd]["groups"])

            for chgroup in storage["commands"][cmd]["groups"]:
                if "channels" in storage["chgroups"][chgroup].keys():
                    self.channel_ids.extend(storage["chgroups"][chgroup]["channels"])

        if "fgroups" in storage["commands"][cmd].keys():
            self.forbid_chgroups.extend(storage["commands"][cmd]["fgroups"])

            for chgroup in storage["commands"][cmd]["fgroups"]:
                self.forbid_channel_ids.extend(storage["chgroups"][chgroup]["channels"])

        self.unrestricted = False
        if (
            "unrestricted" in storage["commands"][cmd].keys()
            and storage["commands"][cmd]["unrestricted"] == "Yes"
        ):
            self.unrestricted = True


@hook.sieve
def check_permissions(bot, bot_event, storage):
    if storage["admin_roles"] is None:
        invalidate_caches(bot, bot_event.event.server)
        return True, None

    cmd = CmdPerms(storage, bot_event.triggered_command)
    # Get a list of user roles
    user_roles = set([i.id for i in bot_event.event.author.roles])

    # Get a list of administrator roles
    allowed_roles = set(storage["admin_roles"] + cmd.owners_ids)

    # Check if either of the categories works
    # If permissions is not empty, then we must restrict to an OR expression of all permission types
    if len(bot_event.hook.permissions) > 0:
        # Other plugins might want custom sieves, so let's not restrict them to just Permission.admin and Permission.bot_owner
        # It becomes their job to create custom permissions
        exists = False
        for perm in bot_event.hook.permissions:
            # Grant bot owners that are listed in the bot config the right to run bot commands
            if perm == permissions.Permission.bot_owner:
                exists = True
                if (
                    "bot_owners" in bot.config
                    and bot_event.event.author.id in bot.config["bot_owners"]
                ):
                    return True, None

            if perm == permissions.Permission.admin:
                exists = True
                if storage["admin_roles"] == None:
                    return (
                        True,
                        "Warning! Admin not set! Use .add_admin_role to set an administrator.",
                    )
                if user_roles & allowed_roles:
                    return True, None

        if exists:
            return False, "You aren't allowed to do that."

    # Check if the command has particular settings
    if cmd.is_customized:
        if cmd.unrestricted:
            return True, None
        if (
            len(cmd.forbid_channel_ids) > 0
            and bot_event.event.channel.id in cmd.forbid_channel_ids
        ):
            bot_event.event.msg.delete_message()
            return (
                False,
                "Command can't be used in "
                + ", ".join(
                    bot_event.event.id_to_chan(i) for i in cmd.forbid_channel_ids
                ),
            )

        if (
            len(cmd.channel_ids) > 0
            and bot_event.event.channel.id not in cmd.channel_ids
        ):
            bot_event.event.msg.delete_message()
            return (
                False,
                "Command can't be used here. Try using it in "
                + ", ".join(bot_event.event.id_to_chan(i) for i in cmd.channel_ids),
            )

    elif (
        storage["default_bot_chan"]
        and bot_event.event.channel.id != storage["default_bot_chan"]
    ):
        bot_event.event.msg.delete_message()
        return (
            False,
            "Command can only be used in "
            + bot_event.event.id_to_chan(storage["default_bot_chan"]),
        )

    return True, None


@hook.on_ready
def map_objects_to_servers(server, storage):
    chgroups[server.id] = SetClearFactory(
        name="chgroups",
        description="Manages groups of channels.\
A group of channels can be associated to a command, so that the command can be used only in the channels listed in the group of channels.",
        data_ref=storage,
        data_format="group_name",
        data_hierarchy='{"group_name":{}}',
        group_name=data_type_string(),
    )

    channels_in_chgroups[server.id] = SetClearFactory(
        name="chgroups",
        description="Manages the channels inside a group of channels.",
        data_ref=storage,
        data_format="channels group_name",
        data_hierarchy='{"group_name":{"channels":[]}}',
        channels=data_type_string(),
        group_name=data_type_dynamic(chgroups[server.id]),
    )

    cgroups_own_cmds[server.id] = SetClearFactory(
        name="commands",
        description="Manage channel groups that are associated to a command.",
        data_ref=storage,
        data_format="cmd groups",
        data_hierarchy='{"cmd":{"groups":[]}}',
        groups=data_type_dynamic(channels_in_chgroups[server.id]),
        cmd=data_type_string(),
    )

    cgroups_forbid_cmds[server.id] = SetClearFactory(
        name="commands",
        description="Manage forbidden channel groups that are associated to a command.",
        data_ref=storage,
        data_format="cmd fgroups",
        data_hierarchy='{"cmd":{"fgroups":[]}}',
        fgroups=data_type_dynamic(channels_in_chgroups[server.id]),
        cmd=data_type_string(),
    )

    ugroups_own_cmds[server.id] = SetClearFactory(
        name="commands",
        description="Manage user groups that are associated to a command.",
        data_ref=storage,
        data_format="cmd owner",
        data_hierarchy='{"cmd":{"owner":[]}}',
        owner=data_type_string(),
        cmd=data_type_string(),
    )

    free_to_use_cmds[server.id] = SetClearFactory(
        name="commands",
        description="Don't restrict commands from being used only in certain channels.",
        data_ref=storage,
        data_format="cmd unrestricted",
        data_hierarchy='{"cmd":{"unrestricted":[]}}',
        cmd=data_type_string(),
        unrestricted=data_type_list(["Yes"]),
    )


#
# Channel groups
#
@hook.command(permissions=Permission.admin, format="chan")
def add_channel_group(send_message, text, server):
    """<group-name> - Create a group of channels"""
    send_message(chgroups[server.id].add_thing(text))


@hook.command(permissions=Permission.admin)
def list_channel_groups(send_message, server):
    """List available groups of channels"""
    ugroups = chgroups[server.id].list_things()

    if len(ugroups) > 0:
        send_message(", ".join(i for i in ugroups))
    else:
        send_message("Empty.")


@hook.command(permissions=Permission.admin, format="chan")
def del_channel_group(send_message, text, server, storage):
    """<group-name> - Delete a group of channels"""

    def dummy_send(text):
        pass

    for cmd in storage["commands"]:
        del_chgroup_from_cmd(dummy_send, cmd + " " + text, server)

    send_message(chgroups[server.id].del_thing(text))


#
# Channels in channel groups
#
@hook.command(permissions=Permission.admin, format="channel channel-group")
def add_chan_to_chgroup(send_message, text, server, str_to_id):
    """<channel channel-group> - Add channel to channel group"""
    send_message(channels_in_chgroups[server.id].add_thing(str_to_id(text)))


@hook.command(permissions=Permission.admin, format="cgroup")
def list_chans_in_chgroup(send_message, text, server, id_to_chan):
    """<channel-group> - List channels in channel-group"""
    vals = channels_in_chgroups[server.id].list_things_for_thing(text, "channels")
    if vals:
        send_message(", ".join(id_to_chan(i) for i in vals))
    else:
        send_message("Empty.")


@hook.command(permissions=Permission.admin, format="channel channel-group")
def del_chan_from_chgroup(send_message, text, server, str_to_id):
    """<channel channel-group> - Delete channel from channel group"""
    send_message(channels_in_chgroups[server.id].del_thing(str_to_id(text)))


#
# Channels that own commands
#
@hook.command(permissions=Permission.admin, format="command channel-group")
def add_chgroup_to_cmd(send_message, text, server):
    """<command channel-group> - Add a channel-group to a command. The command will only be usable in that channel."""
    send_message(cgroups_own_cmds[server.id].add_thing(text))


@hook.command(permissions=Permission.admin, format="cmd")
def list_chgroups_for_cmd(send_message, text, server):
    """<command> - List in what channel-groups command is usable"""
    vals = cgroups_own_cmds[server.id].list_things_for_thing(text, "groups")
    if vals:
        send_message(", ".join(i for i in vals))
    else:
        send_message("Empty.")


@hook.command(permissions=Permission.admin, format="command channel-group")
def del_chgroup_from_cmd(send_message, text, server):
    """<command channel-group> - Delete a user-group from a command's ownership"""
    send_message(cgroups_own_cmds[server.id].del_thing(text))


#
# Channels that forbid commands
#
@hook.command(permissions=Permission.admin, format="command channel-group")
def add_fchgroup_to_cmd(send_message, text, server):
    """<command channel-group> - Add a forbidden channel-group to command"""
    send_message(cgroups_forbid_cmds[server.id].add_thing(text))


@hook.command(permissions=Permission.admin, format="cmd")
def list_fchgroups_for_cmd(send_message, text, server):
    """<command> - List in what channel-groups command is NOT usable"""
    vals = cgroups_forbid_cmds[server.id].list_things_for_thing(text, "fgroups")
    if vals:
        send_message(", ".join(i for i in vals))
    else:
        send_message("Empty.")


@hook.command(permissions=Permission.admin, format="command channel-group")
def del_fchgroup_from_cmd(send_message, text, server):
    """<command channel-group> - Delete a user-group from a command's forbidden list"""
    send_message(cgroups_forbid_cmds[server.id].del_thing(text))


#
# User groups that own commands
#
@hook.command(permissions=Permission.admin, format="cmd owner")
def add_owner_to_cmd(send_message, text, server, str_to_id):
    """<command user-group> - Add a user-group to own a command"""
    text = str_to_id(text)
    send_message(ugroups_own_cmds[server.id].add_thing(text))


@hook.command(permissions=Permission.admin, format="cmd")
def list_owners_for_cmd(send_message, text, server, id_to_role_name):
    """<command> - List what user-groups own a command"""
    vals = ugroups_own_cmds[server.id].list_things_for_thing(text, "owner")
    if vals:
        send_message(", ".join(id_to_role_name(i) for i in vals))
    else:
        send_message("Empty.")


@hook.command(permissions=Permission.admin, format="cmd owner")
def del_owner_from_cmd(send_message, text, server):
    """<command user-group> - Delete user-group from command ownership list"""
    send_message(ugroups_own_cmds[server.id].del_thing(text))


#
# Commands that have no channel restrictions
#
@hook.command(permissions=Permission.admin, format="cmd")
def remove_restrictions_for_cmd(send_message, text, server, str_to_id):
    """<command> - Remove channel restrictions for a command to make it usable on the whole server"""
    send_message(free_to_use_cmds[server.id].add_thing(text + " Yes"))


@hook.command(permissions=Permission.admin, format="cmd")
def is_cmd_unrestricted(send_message, text, server):
    """<command> - Check if command is channel restricted or not"""
    val = free_to_use_cmds[server.id].list_things_for_thing(text, "unrestricted")
    if val:
        send_message("Command is unrestricted")
    else:
        send_message("Command is restricted and may be limited by channel groups")


@hook.command(permissions=Permission.admin, format="cmd")
def restore_restrictions_for_cmd(send_message, text, server):
    """<command user-group> - Restore channel restrictions for command"""
    send_message(free_to_use_cmds[server.id].del_thing(text))


#
# Admin
#
@hook.command(permissions=Permission.admin)
def add_admin_role(text, str_to_id, storage, send_message, server):
    """
    <role> - Add role that can run administrative bot commands.
    """
    role_id = str_to_id(text)

    drole = None
    for role in server.get_roles():
        if role.id == role_id:
            drole = role
            break
        elif role.name == role_id:
            drole = role
            break

    if drole is None:
        send_message(
            "Not a role. Use either role name or mention the role when running the command"
        )
        return

    if "admin_roles" not in storage:
        storage["admin_roles"] = []

    storage["admin_roles"].append(drole.id)
    storage.sync()

    send_message("Done")


@hook.command(permissions=Permission.admin)
def get_admin_roles(send_message, id_to_role_name, storage):
    roles = storage["admin_roles"]
    if not roles:
        send_message("Not set.")
    elif roles and len(roles) > 0:
        str_roles = []
        for i in roles:
            try:
                str_roles.append(id_to_role_name(i))
            except:
                str_roles.append("`Error getting role %s`" % i)

        send_message(", ".join(str_roles))
    else:
        send_message("Empty.")


@hook.command(permissions=Permission.admin, format="role")
def remove_admin_role(send_message, str_to_id, storage, text):
    role_id = str_to_id(text)
    roles = storage["admin_roles"]

    if len(roles) == 1:
        send_message(
            "Cannot remove role, because this is the only admin role for this server"
        )
        return

    if roles and role_id in roles:
        roles.remove(role_id)
        storage.sync()
        send_message("Done.")
    else:
        send_message("Could not find role in admin list.")


#
# Bot channel
#
@hook.command(permissions=Permission.admin, format="chan")
def set_default_bot_channel(text, str_to_id, storage, send_message):
    """
    <channel> - Configure a channel where any bot command can be used, unless otherwise specified by other rules.
    """
    channel_id = str_to_id(text)

    storage["default_bot_chan"] = channel_id

    send_message("Done")


@hook.command(permissions=Permission.admin)
def clear_default_bot_channel(storage, send_message):
    """
    <channel> - Configure a channel where any bot command can be used, unless otherwise specified.
    """
    storage["default_bot_chan"] = None

    send_message("Done")


@hook.command(permissions=Permission.admin)
def list_default_bot_channel(storage, id_to_chan):
    """
    List the built in bot command channel.
    """
    chan = storage["default_bot_chan"]

    if chan:
        return id_to_chan(chan)
    else:
        return "Not set."


@hook.command(permissions=Permission.bot_owner)
def list_bot_servers(bot):
    msg = ""
    for server in bot.backend.get_servers():
        msg += "Name: %s, ID: %s\n" % (server.name, server.id)

    return msg
