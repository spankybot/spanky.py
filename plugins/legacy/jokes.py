import codecs
import os
import random
from spanky.data2.res import readlines

from spanky.hook2 import Hook, EventType

hook = Hook("jokes")


def load_joke_data():
    global yo_momma, do_it, pun, confucious, one_liner, wisdom, book_puns, lawyerjoke, kero_sayings

    yo_momma = readlines("yo_momma.txt", "jokes")
    do_it = readlines("do_it.txt", "jokes")
    pun = readlines("puns.txt", "jokes")
    confucious = readlines("confucious.txt", "jokes")
    one_liner = readlines("one_liners.txt", "jokes")
    wisdom = readlines("wisdom.txt", "jokes")
    book_puns = readlines("book_puns.txt", "jokes")
    lawyerjoke = readlines("lawyerjoke.txt", "jokes")
    kero_sayings = readlines("kero.txt", "jokes")


@hook.command(permissions=["bot_owner"])
def reload_jokes():
    load_joke_data()
    return "Reloaded."


@hook.event(EventType.on_start)
def load_jokes():
    load_joke_data()


@hook.command(server_id="648937029433950218")
def yomomma(text):
    """<nick> - tells a yo momma joke to <nick>"""
    print("bruh")
    target = text.strip()
    return "{}, {}".format(target, random.choice(yo_momma).lower())


@hook.command(autohelp=False)
def doit():
    """- prints a do it line, example: mathmaticians do with a pencil"""
    return random.choice(do_it)


@hook.command(autohelp=False)
def pun():
    """- Come on everyone loves puns right?"""
    print("wtf?????????")
    return random.choice(pun)


@hook.command(autohelp=False)
def confucious():
    """- confucious say man standing on toilet is high on pot."""
    return "Confucious say {}".format(random.choice(confucious).lower())


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
    title = book.split(":")[0].strip()
    author = book.split(":")[1].strip()
    return "{} by {}".format(title, author)


@hook.command(name="boobs")
def boobies(text):
    """- prints boobies!"""
    boob = "\u2299"
    out = text.strip()
    out = out.replace("o", boob).replace("O", boob).replace("0", boob)
    if out == text.strip():
        return "Sorry I couldn't turn anything in '{}' into boobs for you.".format(out)
    return out


@hook.command(name="awesome")
def awesome(text):
    """- Prints a webpage to show <nick> how awesome they are."""
    link = "http://is-awesome.cool/{}"
    nick = text.split(" ")[0]
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
