import codecs
import json
import os
import random

from spanky.plugin import hook

deal_with_it_phrases = [
    'Stop complaining, {}, and',
    'Jesus fuck {}, just',
    'Looks like {} needs to',
    'Ever think that {} just needs to'
]

@hook.on_start()
def load_macros():
    global reaction_macros
    with codecs.open(os.path.join("plugin_data/reaction_macros.json"), encoding="utf-8") as macros:
        reaction_macros = json.load(macros)


@hook.command('dealwithit')
def deal_with_it(text, send_message):
    """<nick> - Tell <nick> in the channel to deal with it. Code located in reactions.py"""
    person_needs_to_deal = text.strip()
    phrase = random.choice(deal_with_it_phrases)
    formated_phrase = phrase.format(person_needs_to_deal)
    send_message('{} {}'.format(formated_phrase, random.choice(reaction_macros['deal_with_it_macros'])))


@hook.command('facepalm')
def face_palm(text, send_message):
    """<nick> - Expresses your frustration with <Nick>. Code located in reactions.py"""
    face_palmer = text.strip()
    send_message('Dammit {} {}'.format(face_palmer, random.choice(reaction_macros['facepalm_macros'])))


@hook.command('headdesk')
def head_desk(text, send_message):
    """<nick> - Hit your head against the desk becausae of <nick>. Code located in reactions.py"""
    idiot = text.strip()
    send_message('{} {}'.format(idiot, random.choice(reaction_macros['head_desk_macros'])))


@hook.command('fetish')
def my_fetish(text, send_message):
    """<nick> - Did some one just mention what your fetish was? Let <nick> know! Code located in reactions.py"""
    person_to_share_fetish_with = text.strip()
    send_message('{} {}'.format(person_to_share_fetish_with, random.choice(reaction_macros['fetish_macros'])))
