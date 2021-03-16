import spanky.utils.carousel as carousel
from spanky.plugin import hook

ROBAC_ID = "456496203040030721"


@hook.command(server_id=ROBAC_ID)
async def tara(send_message, server, event, bot, text):
    """
    Selecteaza tara
    """
    sel = carousel.RoleSelectorInterval(
        server=event.server,
        channel=event.channel,
        title="Țări RoBac",
        first_role="-----[Countries]-----",
        last_role="-----<Countries/>-----",
        max_selectable=1)

    await sel.do_send(event)


@hook.command(server_id=ROBAC_ID)
async def am_luat(send_message, server, event, bot, text):
    """
    Selecteaza bac luat
    """
    sel = carousel.RoleSelectorInterval(
        server=event.server,
        channel=event.channel,
        title="Roluri RoBac",
        first_role="-----[Bac]-----",
        last_role="-----<Bac/>-----",
        max_selectable=1)

    await sel.do_send(event)


@hook.command(server_id=ROBAC_ID)
async def culoare(send_message, server, event, bot, text):
    """
    Selecteaza culoare
    """
    sel = carousel.RoleSelectorInterval(
        server=event.server,
        channel=event.channel,
        title="Culori RoBac",
        first_role="-----[Colors]-----",
        last_role="-----[Vanity Roles]-----",
        max_selectable=1)

    await sel.do_send(event)


@hook.command(server_id=ROBAC_ID)
async def facultate(send_message, server, event, bot, text):
    """
    Selecteaza facultate
    """
    sel = carousel.RoleSelectorInterval(
        server=event.server,
        channel=event.channel,
        title="Facultăți RoBac",
        first_role="-----[Facultati]-----",
        last_role="-----[Earnable]-----",
        max_selectable=1)

    await sel.do_send(event)
