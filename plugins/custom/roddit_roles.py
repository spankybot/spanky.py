import spanky.utils.carousel as carousel
from spanky.plugin import hook

RODDIT_ID = "287285563118190592"


@hook.command(server_id=RODDIT_ID)
async def vreau_culoare(event):
    sel = carousel.RoleSelectorInterval(
        server=event.server,
        channel=event.channel,
        title="r/Romania culori",
        first_role="Albastru canar",
        last_role="Verde mușchi",
        max_selectable=1)
    await sel.do_send(event)

@hook.command(server_id=RODDIT_ID)
async def vreau_rol(event):
    sel = carousel.RoleSelectorInterval(
        server=event.server,
        channel=event.channel,
        title="r/Romania roles",
        first_role="Gospodar",
        last_role="♿",
        max_selectable=5)

    await sel.do_send(event)
