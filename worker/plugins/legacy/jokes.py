import codecs
import os
import random

from SpankyWorker import hook


@hook.on_start()
def load_jokes():
    """
    :type bot: cloudbot.bot.Cloudbot
    """
    global yo_momma, do_it, pun, confucious, one_liner, wisdom, book_puns, lawyerjoke, kero_sayings

    with codecs.open(os.path.join("plugin_data/yo_momma.txt"), encoding="utf-8") as f:
        yo_momma = [line.strip() for line in f.readlines() if not line.startswith("//")]

    with codecs.open(os.path.join("plugin_data/do_it.txt"), encoding="utf-8") as f:
        do_it = [line.strip() for line in f.readlines() if not line.startswith("//")]

    with codecs.open(os.path.join("plugin_data/puns.txt"), encoding="utf-8") as f:
        pun = [line.strip() for line in f.readlines() if not line.startswith("//")]

    with codecs.open(os.path.join("plugin_data/confucious.txt"), encoding="utf-8") as f:
        confucious = [line.strip() for line in f.readlines() if not line.startswith("//")]

    with codecs.open(os.path.join("plugin_data/one_liners.txt"), encoding="utf-8") as f:
        one_liner = [line.strip() for line in f.readlines() if not line.startswith("//")]

    with codecs.open(os.path.join("plugin_data/wisdom.txt"), encoding="utf-8") as f:
        wisdom = [line.strip() for line in f.readlines() if not line.startswith("//")]

    with codecs.open(os.path.join("plugin_data/book_puns.txt"), encoding="utf-8") as f:
        book_puns = [line.strip() for line in f.readlines() if not line.startswith("//")]

    with codecs.open(os.path.join("plugin_data/lawyerjoke.txt"), encoding="utf-8") as f:
        lawyerjoke = [line.strip() for line in f.readlines() if not line.startswith("//")]

    with codecs.open(os.path.join("plugin_data/kero.txt"), encoding="utf-8") as f:
        kero_sayings = [line.strip() for line in f.readlines() if not line.startswith("//")]


@hook.command()
def yomomma(text):
    """<nick> - tells a yo momma joke to <nick>"""
    target = text.strip()
    return '{}, {}'.format(target, random.choice(yo_momma).lower())


@hook.command(autohelp=False)
def doit():
    """- prints a do it line, example: mathmaticians do with a pencil"""
    return random.choice(do_it)


@hook.command(autohelp=False)
def pun():
    """- Come on everyone loves puns right?"""
    return random.choice(pun)


@hook.command(autohelp=False)
def confucious():
    """- confucious say man standing on toilet is high on pot."""
    return 'Confucious say {}'.format(random.choice(confucious).lower())


@hook.command(autohelp=False)
def dadjoke():
    """- love em or hate em, bring on the dad jokes."""
    return random.choice(one_liner)


@hook.command(autohelp=False)
def wisdom():
    """- words of wisdom from various bathroom stalls."""
    return random.choice(wisdom)


@hook.command(autohelp=False)
def bookpun():
    """- Suggests a pun of a book title/author."""
    # suggestions = ["Why not try", "You should read", "You gotta check out"]
    book = random.choice(book_puns)
    title = book.split(':')[0].strip()
    author = book.split(':')[1].strip()
    return "{} by {}".format(title, author)


@hook.command("boobs")
def boobies(text):
    """- prints boobies!"""
    boob = "\u2299"
    out = text.strip()
    out = out.replace('o', boob).replace('O', boob).replace('0', boob)
    if out == text.strip():
        return "Sorry I couldn't turn anything in '{}' into boobs for you.".format(out)
    return out


@hook.command("awesome")
def awesome(text):
    """- Prints a webpage to show <nick> how awesome they are."""
    link = 'http://is-awesome.cool/{}'
    nick = text.split(' ')[0]
    return "{}: I am blown away by your recent awesome action(s). Please read \x02{}\x02".format(
            nick, link.format(nick)
        )


@hook.command(autohelp=False)
def triforce(reply):
    """- returns a triforce!"""
    top = ["\u00a0\u25b2", "\u00a0\u00a0\u25b2", "\u25b2", "\u00a0\u25b2"]
    bottom = ["\u25b2\u00a0\u25b2", "\u25b2 \u25b2", "\u25b2\u25b2"]
    reply(random.choice(top))
    reply(random.choice(bottom))


@hook.command(autohelp=False)
def lawyerjoke():
    """- returns a lawyer joke, so lawyers know how much we hate them"""
    return random.choice(lawyerjoke)
