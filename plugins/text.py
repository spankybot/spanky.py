from spanky.plugin import hook

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
def letters(text):
    """<text> - text to emoji letters"""
    text = text.lower()

    out = ""
    for thing in text:
        if thing.isalpha():
            out += ":regional_indicator_%s:" % thing
        elif thing.isdigit():
            out += d2em[int(thing)]
        else:
            out += thing

    return out
