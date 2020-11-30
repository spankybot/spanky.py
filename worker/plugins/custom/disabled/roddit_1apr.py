from SpankyWorker import hook
from hook.permissions import Permission

from core.event import EventType
import random


SRV = "287285563118190592"
CHIDS = ["287285563118190592"]

THS = ["nu sunt rasist dar", "m-am cacat cu pasiune datorita", "am decis sa ma sterilizez cu", "nu am prietena din simplul motiv ca", "datorita bisericii avem", "iti pierzi masculinitatea daca",
        "am ajuns la concluzia ca",
        "sunt lipicios pentru ca",
        "singurul lucru care am de zis azi este",
        "scuze frate dar nu m-am putut abtine sa nu",
        "azi am mancat o mare portie de",
        "coronavirus e numai vina la"
        ]

#@hook.event(EventType.message)
def alog(event):
    if event.channel.id not in CHIDS:
        return

    if event.author.id == "295665055117344769":
        return

    if not event.text:
        return

    cnt = 0
    for th in THS:
        if th not in event.text:
            cnt += 1

    if cnt == len(THS):
        event.author.send_pm("Mesajul tau din <#%s> a fost sters pentru ca trebuie sa contina una dintre frazele:\n%s" % (event.channel.id, "\n".join(THS)))
        event.msg.delete_message()
        return

#@hook.event(EventType.message_edit)
def log_message_editz(event):
    event.text = event.after.text
    event.text = event.after.text
    alog(event)


@hook.command(permissions=Permission.admin, server_id=SRV)
def asave_chans(server, storage):
    storage["chans"] = {}

    for chan in server.get_channels():
        storage["chans"][chan.id] = chan.name

    storage.sync()

@hook.command(permissions=Permission.admin, server_id=SRV)
def asave_users(server, storage):
    storage["users"] = {}

    for u in server.get_users():
        storage["users"][u.id] = u._raw.display_name

    storage.sync()

@hook.command(permissions=Permission.admin, server_id=SRV)
async def ars_users(server, storage):
    for u in server.get_users():
        if u.id in storage["users"] and u._raw.display_name != storage["users"][u.id]:
            try:
                await u._raw.edit(nick=storage["users"][u.id])
            except:
                pass
    storage.sync()


@hook.command(permissions=Permission.admin, server_id=SRV)
async def ach_users(server, storage):
    for u in server.get_users():
        if u._raw.display_name != "emberi":
            try:
                await u._raw.edit(nick="emberi")
            except:
                pass

    storage.sync()

@hook.command(permissions=Permission.admin, server_id=SRV)
async def ach_chans(server, storage):
    for u in server.get_channels():
        await u._raw.edit(name="csatorna")

    storage.sync()


@hook.command(permissions=Permission.admin, server_id=SRV)
async def ars_chans(server, storage):
    for u in server.get_channels():
        if u.id in storage["chans"] and u._raw.name != storage["chans"][u.id]:
            print("Change " + u.id)
            await u._raw.edit(name=storage["chans"][u.id])
    storage.sync()

