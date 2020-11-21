from core import hook
from hook.permissions import Permission

from core.event import EventType


@hook.event(EventType.message)
async def alog(event):
    if event.channel.id != "728013984430555156":
        return

    if len(event.msg.text.split()) != 3:
        await event.msg.delete_message()
