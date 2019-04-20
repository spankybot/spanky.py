from spanky.plugin import hook
from spanky.plugin.permissions import Permission

@hook.command(format="user")
def avatar(event, text, str_to_id):
    """<user or user-id> - Get someones avatar"""
    text = str_to_id(text)

    for user in event.server.get_users():
        if text == user.name:
            return user.avatar_url
        
        if text == user.id:
            return user.avatar_url
        
    return "Not found"

@hook.command(permissions=Permission.admin)
def set_avatar():
    """
    Set bot avatar
    """
    pass