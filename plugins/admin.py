import os

from spanky.plugin import hook, permissions
from spanky.plugin.permissions import Permission
from spanky.utils.setclearfactory import SetClearFactory, data_type_string, data_type_dynamic

user_groups = {}
users_in_ugroups = {}
chgroups = {}
channels_in_chgroups = {}

@hook.sieve
def check_permissions(bot, event, storage):
    print(storage)
    return False, None

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

#
# User groups
#
@hook.command
def add_user_group(send_message, text, server):
    """<group name> - Create a user group"""
    send_message(user_groups[server.id].add_thing(text))

@hook.command
def list_user_groups(send_message, server):
    """List user groups"""
    ugroups = user_groups[server.id].list_things()

    if len(ugroups) > 0:
        send_message(", ".join(i for i in ugroups))
    else:
        send_message("Empty.")

@hook.command
def del_user_group(send_message, text, server):
    """<group name> - Deletes a user group"""
    send_message(user_groups[server.id].del_thing(text))

#
# Users in user groups
#
@hook.command
def add_user_to_ugroup(send_message, text, server, str_to_id):
    """<user user-group> - Add user to user group"""
    send_message(users_in_ugroups[server.id].add_thing(str_to_id(text)))

@hook.command
def list_users_in_ugroup(send_message, text, server, user_id_to_name):
    vals = users_in_ugroups[server.id].list_things_for_thing(text, "users")
    if vals:
        send_message(", ".join(user_id_to_name(i) for i in vals))
    else:
        send_message("Empty.")

@hook.command
def del_user_from_ugroup(send_message, text, server, str_to_id):
    """<user user-group> - Delete user from user group"""
    send_message(users_in_ugroups[server.id].del_thing(str_to_id(text)))

#
# Channel groups
#
@hook.command
def add_channel_group(send_message, text, server):
    """<group name> - Create a group of channels"""
    send_message(chgroups[server.id].add_thing(text))

@hook.command
def list_channel_groups(send_message, server):
    """List available groups of channels"""
    ugroups = chgroups[server.id].list_things()

    if len(ugroups) > 0:
        send_message(", ".join(i for i in ugroups))
    else:
        send_message("Empty.")

@hook.command
def del_channel_group(send_message, text, server):
    """<group name> - Delete a group of channels"""
    send_message(chgroups[server.id].del_thing(text))

#
# Channels in channel groups
#
@hook.command
def add_chan_to_chgroup(send_message, text, server, str_to_id):
    """<channel channel-group> - Add channel to channel group"""
    send_message(channels_in_chgroups[server.id].add_thing(str_to_id(text)))

@hook.command
def list_chans_in_chgroup(send_message, text, server, id_to_chan):
    """<channel-group> - List channels in channel-group"""
    vals = channels_in_chgroups[server.id].list_things_for_thing(text, "channels")
    if vals:
        send_message(", ".join(id_to_chan(i) for i in vals))
    else:
        send_message("Empty.")

@hook.command
def del_chan_from_chgroup(send_message, text, server, str_to_id):
    """<channel channel-group> - Delete channel from channel group"""
    send_message(channels_in_chgroups[server.id].del_thing(str_to_id(text)))

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
    