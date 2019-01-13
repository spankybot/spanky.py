import os

from spanky.plugin import hook, permissions
from spanky.plugin.permissions import Permission
from spanky.utils.setclearfactory import SetClearFactory, data_type_string, data_type_dynamic

user_groups = {}
users_in_ugroups = {}
chgroups = {}
channels_in_chgroups = {}
cgroups_own_cmds = {}
cgroups_forbid_cmds = {}
ugroups_own_cmds = {}

class CmdPerms():
    def __init__(self, storage, cmd):
        self.cmd = cmd

        self.is_customized = False
        self.owner_groups = []
        self.owners_ids = []
        self.chgroups = []
        self.channel_ids = []
        self.forbid_chgroups = []
        self.forbid_channel_ids = []

        if cmd in storage["commands"]:
            self.is_customized = True
        else:
            return

        if "owner" in storage["commands"][cmd].keys():
            self.owner_groups.extend(storage["commands"][cmd]["owner"])

            for owner_group in storage["commands"][cmd]["owner"]:
                self.owners_ids.extend(storage["owners"][owner_group]["users"])

        if "groups" in storage["commands"][cmd].keys():
            self.chgroups.extend(storage["commands"][cmd]["groups"])

            for chgroup in storage["commands"][cmd]["groups"]:
                if "channels" in storage["chgroups"][chgroup].keys():
                    self.channel_ids.extend(storage["chgroups"][chgroup]["channels"])

        if "fgroups" in storage["commands"][cmd].keys():
            self.forbid_chgroups.extend(storage["commands"][cmd]["fgroups"])

            for chgroup in storage["commands"][cmd]["fgroups"]:
                self.forbid_channel_ids.extend(storage["chgroups"][chgroup]["channels"])


@hook.sieve
def check_permissions(bot, bot_event, storage):
    user_roles = bot_event.event.author.roles

    if bot_event.hook.permissions == permissions.Permission.admin:
        if storage["admin_roles"] == None:
            return True, "Warning! Admin not set!"
        for role in user_roles:
            if role.id in storage["admin_roles"]:
                return True, None
        return False, "You're not an admin."

    cmd = CmdPerms(storage, bot_event.triggered_command)

    # Check if the command has particular settings
    if cmd.is_customized:
        if len(cmd.owners_ids) > 0 and bot_event.event.author.id not in cmd.owners_ids:
            return False, "You can't use this command"

        if len(cmd.forbid_channel_ids) > 0 and bot_event.event.channel.id in cmd.forbid_channel_ids:
            return False, "Command can't be used in " + \
                ", ".join(bot_event.event.id_to_chan(i) for i in cmd.forbid_channel_ids)

        if len(cmd.channel_ids) > 0 and bot_event.event.channel.id not in cmd.channel_ids:
            return False, "Command can't be used here. Try using it in " + \
                ", ".join(bot_event.event.id_to_chan(i) for i in cmd.channel_ids)

    elif storage["default_bot_chan"] and bot_event.event.channel.id != storage["default_bot_chan"]:
        return False, "Command can only be used in " + bot_event.event.id_to_chan(storage["default_bot_chan"])

    return True, None

@hook.on_ready
def map_objects_to_servers(server, storage):
    user_groups[server.id] = SetClearFactory(name="owners",
                          description="Manage user groups. A user group can be set to 'own' a command, \
so that only users of the user group can use that command.",
                          data_ref=storage,
                          data_format="group_name",
                          data_hierarchy='{"group_name":{}}',
                          group_name=data_type_string())

    users_in_ugroups[server.id] = SetClearFactory(name="owners",
                                 description="Manage users inside user groups.",
                                 data_ref=storage,
                                 data_format="users group_name",
                                 data_hierarchy='{"group_name":{"users":[]}}',
                                 group_name=data_type_dynamic(user_groups[server.id]),
                                 users=data_type_string())

    chgroups[server.id] = SetClearFactory(name="chgroups",
                            description="Manages groups of channels.\
A group of channels can be associated to a command, so that the command can be used only in the channels listed in the group of channels.",
                            data_ref=storage,
                            data_format="group_name",
                            data_hierarchy='{"group_name":{}}',
                            group_name=data_type_string())

    channels_in_chgroups[server.id] = SetClearFactory(name="chgroups",
                                     description="Manages the channels inside a group of channels.",
                                     data_ref=storage,
                                     data_format="channels group_name",
                                     data_hierarchy='{"group_name":{"channels":[]}}',
                                     channels=data_type_string(),
                                     group_name=data_type_dynamic(chgroups[server.id]))

    cgroups_own_cmds[server.id] = SetClearFactory(name="commands",
                                    description="Manage channel groups that are associated to a command.",
                                    data_ref=storage,
                                    data_format="cmd groups",
                                    data_hierarchy='{"cmd":{"groups":[]}}',
                                    groups=data_type_dynamic(channels_in_chgroups[server.id]),
                                    cmd=data_type_string())

    cgroups_forbid_cmds[server.id] = SetClearFactory(name="commands",
                                description="Manage channel groups that are associated to a command.",
                                data_ref=storage,
                                data_format="cmd fgroups",
                                data_hierarchy='{"cmd":{"fgroups":[]}}',
                                fgroups=data_type_dynamic(channels_in_chgroups[server.id]),
                                cmd=data_type_string())

    ugroups_own_cmds[server.id] = SetClearFactory(name="commands",
                                   description="Manage user groups that are associated to a command.",
                                   data_ref=storage,
                                   data_format="cmd owner",
                                   data_hierarchy='{"cmd":{"owner":[]}}',
                                   owner=data_type_dynamic(user_groups[server.id]),
                                   cmd=data_type_string())



#
# User groups
#
@hook.command(permissions=Permission.admin, format="user")
def add_user_group(send_message, text, server):
    """<group name> - Create a user group"""
    send_message(user_groups[server.id].add_thing(text))

@hook.command(permissions=Permission.admin)
def list_user_groups(send_message, server):
    """List user groups"""
    ugroups = user_groups[server.id].list_things()

    if len(ugroups) > 0:
        send_message(", ".join(i for i in ugroups))
    else:
        send_message("Empty.")

@hook.command(permissions=Permission.admin, format="user")
def del_user_group(send_message, text, server, storage):
    """<group name> - Deletes a user group"""
    def dummy_send(text):
        pass

    for cmd in storage["commands"]:
        del_owner_from_cmd(dummy_send, cmd + " " + text, server)

    send_message(user_groups[server.id].del_thing(text))

#
# Users in user groups
#
@hook.command(permissions=Permission.admin, format="user ugroup")
def add_user_to_ugroup(send_message, text, server, str_to_id):
    """<user user-group> - Add user to user group"""
    send_message(users_in_ugroups[server.id].add_thing(str_to_id(text)))

@hook.command(permissions=Permission.admin, format="ugroup")
def list_users_in_ugroup(send_message, text, server, user_id_to_name):
    vals = users_in_ugroups[server.id].list_things_for_thing(text, "users")
    if vals:
        send_message(", ".join(user_id_to_name(i) for i in vals))
    else:
        send_message("Empty.")

@hook.command(permissions=Permission.admin, format="user ugroup")
def del_user_from_ugroup(send_message, text, server, str_to_id):
    """<user user-group> - Delete user from user group"""
    send_message(users_in_ugroups[server.id].del_thing(str_to_id(text)))

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
    """<channel-group command> - Add a channel-group to a command. The command will only be usable in that channel."""
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
def add_owner_to_cmd(send_message, text, server):
    """<command user-group> - Add a user-group to own a command"""
    send_message(ugroups_own_cmds[server.id].add_thing(text))

@hook.command(permissions=Permission.admin, format="cmd")
def list_owners_for_cmd(send_message, text, server):
    """<command> - List what user-groups own a command"""
    vals = ugroups_own_cmds[server.id].list_things_for_thing(text, "owner")
    if vals:
        send_message(", ".join(i for i in vals))
    else:
        send_message("Empty.")

@hook.command(permissions=Permission.admin, format="cmd owner")
def del_owner_from_cmd(send_message, text, server):
    """<command user-group> - Delete user-group from command ownership list"""
    send_message(ugroups_own_cmds[server.id].del_thing(text))

#
# Admin
#
@hook.command(permissions=Permission.admin, format="role")
def add_admin_role(text, str_to_id, storage, send_message):
    """
    <role> - Add role that can run administrative bot commands.
    """
    role_id = str_to_id(text)

    if "admin_roles" not in storage:
        storage["admin_roles"] = []

    storage["admin_roles"].append(role_id)
    storage.sync()

    send_message("Done")

@hook.command(permissions=Permission.admin)
def get_admin_roles(send_message, id_to_role_name, storage):
    roles = storage["admin_roles"]
    if not roles:
        send_message("Not set.")
    elif roles and len(roles) > 0:
        send_message(", ".join(id_to_role_name(i) for i in roles))
    else:
        send_message("Empty.")


@hook.command(permissions=Permission.admin, format="role")
def remove_admin_role(send_message, str_to_id, storage, text):
    role_id = str_to_id(text)
    roles = storage["admin_roles"]

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

