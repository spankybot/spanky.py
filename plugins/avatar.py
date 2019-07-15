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

@hook.command(permissions=Permission.bot_owner)
async def set_avatar(event, async_set_avatar):
    """
    Set bot avatar
    """
    try:
        for img in event.image:
            img.fetch_url()
            await async_set_avatar(img._raw[0])
            return
    except:
        import traceback
        traceback.print_exc()
