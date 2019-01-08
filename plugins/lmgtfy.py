import requests

from spanky.plugin import hook
from spanky.utils import web


@hook.command("lmgtfy")
def lmgtfy(text):
    """[phrase] - gets a lmgtfy.com link for the specified phrase"""

    link = "http://lmgtfy.com/?q={}".format(requests.utils.quote(text))

    return web.try_shorten(link)
