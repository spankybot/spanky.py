from SpankyWorker import hook
from utils.discord_utils import get_role_by_name, add_role_from_list, remove_given_role_from_list

BM_ID = "349583192921079808"

no_role = "no role".lower()


@hook.command(server_id=BM_ID)
async def verified(server, author, event):
    """Get server access rights"""
    verif = get_role_by_name(server, "Verified")

    author.add_role(verif)

    await event.msg.async_add_reaction(u"👍")


@hook.command(server_id=BM_ID)
def charlie(send_message, server, event, text):
    """
    Assign a role
    """
    return add_role_from_list(
        "--- START BOT ROLES ---",
        "--- END BOT ROLES ---",
        server,
        event,
        send_message,
        text,
        max_assignable=4)


@hook.command(server_id=BM_ID)
def nocharlie(send_message, server, event, text):
    """
    Unassign a role
    """
    return remove_given_role_from_list(
        "--- START BOT ROLES ---",
        "--- END BOT ROLES ---",
        server,
        event,
        send_message,
        text)
