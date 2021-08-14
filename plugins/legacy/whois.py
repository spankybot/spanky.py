"""
whois.py
Provides a command to allow users to look up information on domain names.
"""

import sys
import whois as pythonwhois
from contextlib import suppress

from spanky.plugin import hook

def get_data(val):
    print(val, type(val))
    if type(val) is list:
        return val[0]
    return val

@hook.command
def whois(text, reply):
    """<domain> - Does a whois query on <domain>."""
    if pythonwhois is None:
        return "The pythonwhois library does not work on this version of Python."

    domain = text.strip().lower()

    try:
        data = pythonwhois.whois(domain)
    except:
        reply("Invalid input.")
        raise

    info = []

    # We suppress errors here because different domains provide different data fields
    with suppress(KeyError):
        info.append(("Registrar", get_data(data["registrar"])))

    with suppress(KeyError):
        info.append(("Registered", get_data(data["creation_date"]).strftime("%d-%m-%Y")))

    with suppress(KeyError):
        info.append(("Expires", get_data(data["expiration_date"]).strftime("%d-%m-%Y")))

    if not info:
        return "No information returned."

    info_text = ", ".join("{name}: {info}".format(name=name, info=i) for name, i in info)
    return "{} - {}".format(domain, info_text)
