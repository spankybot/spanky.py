import os

from spanky.plugin import hook, permissions
from spanky.plugin.permissions import Permission

@hook.command(permissions=Permission.admin)
def set_admin(text, str_to_id, permission_mgr, send_message):
    """
    Set user that owns the bot on a server.
    """
    user_id = str_to_id(text)
    
    err = permission_mgr.set_admin(user_id)
    
    if not err:
        send_message("Done")
    else:
        send_message(err)
        
@hook.command(permissions=Permission.admin)
async def get_admin(async_send_message, id_to_user, permission_mgr):
    admin_id = permission_mgr.get_admin()
    
    if admin_id:
        sent = await async_send_message("The admin is set to: %s" % id_to_user(admin_id))
        print(sent)
    else:
        await async_send_message("No admin set")
    
@hook.command(permissions=Permission.admin, format="chan")
def set_default_bot_channel(text, str_to_id, permission_mgr, send_message):
    """
    <channel> - Configure a channel where any bot command can be used, unless otherwise specified by other rules.
    """
    channel_id = str_to_id(text)
    
    permission_mgr.set_default_bot_channel(channel_id)
    
    send_message("Done")
    
@hook.command(permissions=Permission.admin)
def clear_default_bot_channel(permission_mgr, send_message):
    """
    <channel> - Configure a channel where any bot command can be used, unless otherwise specified.
    """
    permission_mgr.set_default_bot_channel(None)
    
    send_message("Done")
    
@hook.command(permissions=Permission.admin)
def list_default_bot_channel(permission_mgr, id_to_chan):
    """
    List the built in bot command channel.
    """
    chan = permission_mgr.list_default_bot_channel()
    
    if chan:
        return id_to_chan(chan)
    else:
        return "Not set."
    