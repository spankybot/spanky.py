import os

from spanky.plugin import hook
from spanky.plugin.permissions import Permission

@hook.command(format="role cmd")
def add_role_to_cmd(text, str_to_id, permission_mgr, send_message, bot):
    """
    <role cmd> - Adds a server role to own a command
    """
    role_id = str_to_id(text.split()[0])
    cmd = str_to_id(text.split()[1])
    
    if cmd not in bot.plugin_manager.commands:
        send_message("Invalid command")
        return
    
    err = permission_mgr.add_role_to_cmd(role_id, cmd)
    
    if not err:
        send_message("Done")
    else:
        send_message(err)