from core import hook

d2em = {
    1: ":one:",
    2: ":two:",
    3: ":three:",
    4: ":four:",
    5: ":five:",
    6: ":six:",
    7: ":seven:",
    8: ":eight:",
    9: ":nine:",
    0: ":zero:",
}


@hook.command
def letters(event):
    """<text> - text to emoji letters"""
    text = event.msg._raw.clean_content.split(maxsplit=1)[1].lower()

    out = ""
    for thing in text:
        if thing.isalpha():
            out += ":regional_indicator_%s:" % thing
        elif thing.isdigit():
            out += d2em[int(thing)]
        else:
            out += thing

    return out
