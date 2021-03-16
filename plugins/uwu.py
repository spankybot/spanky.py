import random
from spanky.plugin import hook

# ported from https://github.com/zuzak/owo/blob/master/owo.js

prefixes = [
    '<3 ',
    '0w0 ',
    'H-hewwo?? ',
    'HIIII! ',
    'Haiiii! ',
    'Huohhhh. ',
    'OWO ',
    'OwO ',
    'UwU '
]

suffixes = [
    ' :3',
    ' UwU',
    ' ÙωÙ',
    ' ʕʘ‿ʘʔ',
    ' ʕ•̫͡•ʔ',
    ' >_>',
    ' ^_^',
    '..',
    ' Huoh.',
    ' ^-^',
    ' ;_;',
    ' ;-;',
    ' xD',
    ' x3',
    ' :D',
    ' :P',
    ' ;3',
    ' XDDD',
    ', fwendo',
    ' ㅇㅅㅇ',
    ' (人◕ω◕)',
    '（＾ｖ＾）',
    ' Sigh.',
    ' x3',
    ' ._.',
    ' (　\'◟ \')',
    ' (• o •)',
    ' (；ω；)',
    ' >_<'
]

substitutions = {
    'r': 'w',
    'l': 'w',
    'R': 'W',
    'L': 'W',
    # 'ow': 'OwO',
    'no': 'nu',
    'has': 'haz',
    'have': 'haz',
    'you': 'uu',
    'the ': 'da ',
    'The ': 'Da '
}


def add_affixes(s):
    return random.choice(prefixes) + s + random.choice(suffixes)


def substitute(s):
    for key, val in substitutions.items():
        s = s.replace(key, val)

    return s


@hook.command()
def uwu(text):
    """
    <text> - translate text to UwU
    """

    return add_affixes(substitute(text))
