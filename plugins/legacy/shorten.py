from spanky.utils import web
from spanky.hook2.hook2 import Hook

hook = Hook("shorten")


@hook.command()
def shorten(text, reply):
    """<url> [custom] - shortens a url with [custom] as an optional custom shortlink"""
    args = text.split()
    url = args[0]
    custom = args[1] if len(args) > 1 else None

    try:
        return web.shorten(url, custom=custom)
    except web.ServiceError as e:
        reply(e.message)
        raise


@hook.command()
def expand(text, reply):
    """<url> - unshortens <url>"""
    args = text.split()
    url = args[0]

    try:
        return web.expand(url)
    except web.ServiceError as e:
        reply(e.message)
        raise


@hook.command()
def isgd(text, reply):
    """<url> [custom] - shortens a url using is.gd with [custom] as an optional custom shortlink,
    or unshortens <url> if already short"""
    args = text.split()
    url = args[0]
    custom = args[1] if len(args) > 1 else None

    try:
        if "is.gd" in url:
            return web.expand(url, "is.gd")
        else:
            return web.shorten(url, custom, "is.gd")
    except web.ServiceError as e:
        reply(e.message)
        raise
