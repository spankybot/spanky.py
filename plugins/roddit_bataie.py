#-*- coding: utf-8 -*-
import datetime
from spanky.plugin import hook
from plugins.discord_utils import *
from spanky.utils import time_utils
from spanky.plugin.event import EventType

BATAIE_CHALLENGE_TIME = 15 * 60
BATAIE_TIME = 15 * 60

EMOJI_UP = u'⬆'
EMOJI_DOWN = u'⬇'

RODDIT_ID = "287285563118190592"
BATAIE_CHAN = "576369175782490115"

roddit = None
rstorage = None

@hook.event(EventType.message)
async def do_react(event, bot):
    if event.channel.id != BATAIE_CHAN or event.author.id == bot.get_own_id():
        return
    else:
        await event.msg.async_add_reaction(EMOJI_UP)
        await event.msg.async_add_reaction(EMOJI_DOWN)

@hook.event(EventType.reaction_add)
async def do_score(event):
    try:
        if event.channel.id != BATAIE_CHAN:
            return

        if rstorage["bataie_data"] is None:
            return

        if event.msg.author.id not in rstorage["bataie_data"]["score"]:
            rstorage["bataie_data"]["score"][event.msg.author.id] = 0

        if event.reaction.emoji.name == EMOJI_DOWN:
            rstorage["bataie_data"]["score"][event.msg.author.id] -= 1

        if event.reaction.emoji.name == EMOJI_UP:
            rstorage["bataie_data"]["score"][event.msg.author.id] += 1

        rstorage.sync()

    except:
        import traceback
        traceback.print_exc()


@hook.on_ready(server_id=RODDIT_ID)
def init_bataie(storage, server):
    global roddit
    global rstorage

    roddit = server
    rstorage = storage

    if storage["bataie"] is None:
        storage["bataie"] = []
        storage.sync()
        return

def stop_bataie():
    role = get_role_by_name(roddit, "bataie")

    user_chlgr = get_user_by_id(roddit, rstorage["bataie_data"]["batausi"][0])
    user_chlgd = get_user_by_id(roddit, rstorage["bataie_data"]["batausi"][1])

    user_chlgr.remove_role(role)
    user_chlgd.remove_role(role)

    scor = rstorage["bataie_data"]["score"]

    rstorage["bataie_data"] = None
    rstorage.sync()

    return scor

def print_scor(results):
    msg = "Bataia s-a terminat. Scorul a fost: \n"

    for usr, score in results.items():
        msg += "<@%s>: %s\n" % (usr, score)

    return msg

@hook.command(server_id=RODDIT_ID)
def end_bataie(author):
    if author.id in rstorage["bataie_data"]["batausi"]:
        results = stop_bataie()
        return print_scor(results)

@hook.periodic(1)
def check_bataie(send_message):
    if rstorage is None or rstorage["bataie_data"] is None:
        return

    if time_utils.tnow() - rstorage["bataie_data"]["start_time"] > BATAIE_TIME:
        send_message(print_scor(stop_bataie()), "576369175782490115", roddit)

@hook.command(server_id=RODDIT_ID)
def bataie(send_message, text, str_to_id, author, server):
    global rstorage

    challenger = author.id
    challenged = str_to_id(text)

    if challenged == "" or not challenged.isdigit():
        send_message("Trebuie sa specifici un user")
        return

    if challenger == challenged:
        send_message("Nu poti sa te provoci pe tine, prostule.")
        return

    #if rstorage["bataie_data"] is not None:
        #send_message("Bataie activa. Mai asteapta")
        #return

    match = False
    for elem in list(rstorage["bataie"]):
        if time_utils.tnow() - elem["time"] > BATAIE_CHALLENGE_TIME:
            rstorage["bataie"].remove(elem)
            rstorage.sync()

        if elem["challenged"] == challenged and elem["challenger"] == challenger:
            send_message("Exista deja o provocare de la tine pentru celalalt user.")

        if elem["challenged"] == challenger and elem["challenger"] == challenged:
            if rstorage["bataie_data"] is not None:
                send_message("Se desfasoara deja o bataie, mai asteapta")
                return

            rstorage["bataie"].remove(elem)
            rstorage.sync()

            send_message("Incepe bataia! Aveti 15 minute la dispozitie. Daca vreti sa terminati mai devreme unul dintre voi trebuie sa dea comanda `.end_bataie`")
            match = True

            # Set roles and start it
            role = get_role_by_name(server, "bataie")
            user_chlgr = get_user_by_id(server, challenger)
            user_chlgd = get_user_by_id(server, challenged)

            user_chlgr.add_role(role)
            user_chlgd.add_role(role)

            rstorage["bataie_data"] = {
                    "start_time": time_utils.tnow(),
                    "batausi": [challenger, challenged],
                    "score": {
                        challenger: 0,
                        challenged: 0
                        }
                    }
            rstorage.sync()

            send_message("<@%s> vs. <@%s>" % (challenger, challenged), "576369175782490115", roddit)

            break

    if match == False:
        send_message("<@%s> a fost provocat sa intre pe canalul de bataie! Acum trebuie sa astepti sa te provoace si el pe tine ca sa incepeti bataia! Daca nu accepta in 15 minute, provocarea va expira." % challenged)
        rstorage["bataie"].append(
            {
                "challenger": challenger,
                "challenged": challenged,
                "time": time_utils.tnow()
            })
        rstorage.sync()
