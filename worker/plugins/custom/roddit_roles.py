import utils.carousel as carousel
from SpankyWorker import hook

RODDIT_ID = "287285563118190592"


@hook.command(server_id=RODDIT_ID)
async def vreau_culoare(event):
    sel = carousel.RoleSelectorInterval(
        server=event.server,
        channel=event.channel,
        title="r/Romania culori",
        first_role="----- START Culori -----",
        last_role="------- END Culori -------",
        max_selectable=1)
    await sel.do_send(event)


@hook.command(server_id=RODDIT_ID)
async def vreau_rol(event):
    sel = carousel.RoleSelectorInterval(
        server=event.server,
        channel=event.channel,
        title="r/Romania roles",
        first_role="---- START Grupuri ----",
        last_role="---- END Grupuri ----",
        max_selectable=5)

    await sel.do_send(event)


@hook.command(server_id=RODDIT_ID)
async def vreau_joc(event):
    sel = carousel.RoleSelectorInterval(
        server=event.server,
        channel=event.channel,
        title="r/Romania roles",
        first_role="---- START Jocuri ----",
        last_role="---- END Jocuri ----",
        max_selectable=5)

    await sel.do_send(event)
