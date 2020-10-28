import random
from collections import defaultdict

from core import hook
from utils import formatting

table_status = defaultdict(lambda: None)
USE_FLIPPERS = True

replacements = {
    'a': 'ɐ',
    'b': 'q',
    'c': 'ɔ',
    'd': 'p',
    'e': 'ǝ',
    'f': 'ɟ',
    'g': 'ƃ',
    'h': 'ɥ',
    'i': 'ᴉ',
    'j': 'ɾ',
    'k': 'ʞ',
    'l': 'ן',
    'm': 'ɯ',
    'n': 'u',
    'o': 'o',
    'p': 'd',
    'q': 'b',
    'r': 'ɹ',
    's': 's',
    't': 'ʇ',
    'u': 'n',
    'v': 'ʌ',
    'w': 'ʍ',
    'x': 'x',
    'y': 'ʎ',
    'z': 'z',
    '?': '¿',
    '.': '˙',
    ',': '\'',
    '(': ')',
    '<': '>',
    '[': ']',
    '{': '}',
    '\'': ',',
    '_': '‾'}

# append an inverted form of replacements to itself, so flipping works both ways
replacements.update(dict((v, k) for k, v in replacements.items()))

flippers = ["( ﾉ⊙︵⊙）ﾉ", "(╯°□°）╯", "( ﾉ♉︵♉ ）ﾉ"]
table_flipper = "┻━┻ ︵ヽ(`Д´)ﾉ︵ ┻━┻"


@hook.command
def flip_text(text, channel, send_message):
    """<text> - Flips <text> over."""
    global table_status
    # table_status = defaultdict(False)
    if USE_FLIPPERS:
        if text in ['table', 'tables']:
            send_message(random.choice([random.choice(flippers) + " ︵ " + "\u253B\u2501\u253B", table_flipper]))
            table_status[channel.id] = True
        elif text == "5318008":
            out = "BOOBIES"
            send_message(random.choice(flippers) + " ︵ " + out)
        elif text == "BOOBIES":
            out = "5318008"
            send_message(random.choice(flippers) + " ︵ " + out)
        else:
            send_message(random.choice(flippers) + " ︵ " + formatting.multi_replace(text[::-1], replacements))
    else:
        send_message(formatting.multi_replace(text[::-1], replacements))


@hook.command(autohelp=False)
def table(text):
    """<text> - (╯°□°）╯︵ <ʇxǝʇ>"""
    return random.choice(flippers) + " ︵ " + formatting.multi_replace(text[::-1].lower(), replacements)

@hook.command
def fix(text, channel, send_message):
    """<text> - fixes a flipped over table. ┬─┬ノ(ಠ_ಠノ)"""
    global table_status
    if text in ['table', 'tables']:
        if table_status[channel.id] is True:
            send_message("┬─┬ノ(ಠ_ಠノ)")
            table_status[channel.id] = False
        else:
            send_message("no tables have been turned over in {}, thanks for checking!".format(chan))
    else:
        send_message(flip(text, reply, send_message, chan))
