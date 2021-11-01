"""
web.py

Contains functions for interacting with web services.

Created by:
    - Bjorn Neergaard <https://github.com/neersighted>

Maintainer:
    - Luke Rogers <https://github.com/lukeroge>

License:
    GPL v3
"""

import json

import asyncio
import requests

# Constants

DEFAULT_SHORTENER = "is.gd"
DEFAULT_PASTEBIN = "hastebin"

HASTEBIN_SERVER = "https://hastebin.com"

SNOONET_PASTE = "https://paste.snoonet.org"


# Shortening / pasting

# Public API


def shorten(url, custom=None, service=DEFAULT_SHORTENER):
    impl = shorteners[service]
    return impl.shorten(url, custom)


def try_shorten(url, custom=None, service=DEFAULT_SHORTENER):
    impl = shorteners[service]
    return impl.try_shorten(url, custom)


def expand(url, service=None):
    if service:
        impl = shorteners[service]
    else:
        impl = None
        for name in shorteners:
            if name in url:
                impl = shorteners[name]
                break

        if impl is None:
            impl = Shortener()

    return impl.expand(url)


def paste(data, ext="txt", service=DEFAULT_PASTEBIN):
    impl = pastebins[service]
    return impl.paste(data, ext)


class ServiceError(Exception):
    def __init__(self, message, request):
        self.message = message
        self.request = request

    def __str__(self):
        return "[HTTP {}] {}".format(self.request.status_code, self.message)


class Shortener:
    def __init__(self):
        pass

    def shorten(self, url, custom=None):
        return url

    def try_shorten(self, url, custom=None):
        try:
            return self.shorten(url, custom)
        except ServiceError:
            return url

    def expand(self, url):
        r = requests.get(url, allow_redirects=False)

        if "location" in r.headers:
            return r.headers["location"]
        else:
            raise ServiceError("That URL does not exist", r)


class Pastebin:
    def __init__(self):
        pass

    def paste(self, data, ext):
        raise NotImplementedError


# Internal Implementations

shorteners = {}
pastebins = {}


def _shortener(name):
    def _decorate(impl):
        shorteners[name] = impl()

    return _decorate


def _pastebin(name):
    def _decorate(impl):
        pastebins[name] = impl()

    return _decorate


@_shortener("is.gd")
class Isgd(Shortener):
    def shorten(self, url, custom=None):
        p = {"url": url, "shorturl": custom, "format": "json"}
        r = requests.get("http://is.gd/create.php", params=p)
        j = r.json()

        if "shorturl" in j:
            return j["shorturl"]
        else:
            raise ServiceError(j["errormessage"], r)

    def expand(self, url):
        p = {"shorturl": url, "format": "json"}
        r = requests.get("http://is.gd/forward.php", params=p)
        j = r.json()

        if "url" in j:
            return j["url"]
        else:
            raise ServiceError(j["errormessage"], r)


@_pastebin("hastebin")
class Hastebin(Pastebin):
    def paste(self, data, ext):
        r = requests.post(HASTEBIN_SERVER + "/documents", data=data)
        j = r.json()

        if r.status_code is requests.codes.ok:
            return "{}/{}.{}".format(HASTEBIN_SERVER, j["key"], ext)
        else:
            raise ServiceError(j["message"], r)


@_pastebin("snoonet")
class SnoonetPaste(Pastebin):
    def paste(self, data, ext):

        params = {"text": data, "expire": "1d"}
        r = requests.post(SNOONET_PASTE + "/paste/new", params=params)
        return "{}".format(r.url)
        if r.status_code is requests.codes.ok:
            return "{}".format(r.url)
        else:
            return ServiceError(r.status_code, r)
