"""
cryptocurrency.py

A plugin that uses the CoinMarketCap JSON API to get values for cryptocurrencies.

Created By:
    - Luke Rogers <https://github.com/lukeroge>

License:
    GPL v3
"""
from datetime import datetime
from urllib.parse import quote_plus

import requests

from core import hook

API_URL = "https://www.coinbase.com/api/v2/assets/prices?base={}&filter=listed&resolution=latest"


class Alias:
    def __init__(self, name, cmd, nocmd=True):
        self.name = name
        self.cmds = cmd
        self.nocmd = nocmd


ALIASES = (
    Alias('btc', 'btc', False),
    Alias('ltc', 'ltc', False),
    Alias('eth', 'eth', False),
    Alias('bch', 'bch'),
    Alias('xrp', 'xrp'),
    Alias('eos', 'eos'),
)


def get_request(ticker, currency):
    return requests.get(API_URL.format(quote_plus(currency)))


def alias_wrapper(alias):
    def func(text, reply):
        return crypto_command(" ".join((alias.name, text)), reply)

    func.__doc__ = """- Returns the current {} value""".format(alias.name)
    func.__name__ = alias.name + "_alias"

    return func


def init_aliases():
    for alias in ALIASES:
        if alias.nocmd:
            continue
        _hook = alias_wrapper(alias)
        globals()[_hook.__name__] = hook.command(
            alias.cmds, autohelp=False)(_hook)


@hook.command()
def serak():
    msg = "\n"
    for cur in ALIASES:
        msg += crypto_command(cur.name, None) + "\n"

    return msg

# main command
@hook.command("crypto")
def crypto_command(text, reply):
    """<ticker> [currency] - Returns current value of a cryptocurrency"""
    args = text.split()
    ticker = args.pop(0)

    if not args:
        currency = 'USD'
    else:
        currency = args.pop(0).upper()

    try:
        request = get_request(ticker, currency)
        request.raise_for_status()
    except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError) as e:
        reply("Could not get value")
        raise

    data = request.json()

    elem = None
    for el in data["data"]:
        if el["base"].lower() == ticker:
            elem = el
            break

    if not elem:
        return "Could not find ticker"

    return "`{} || {:.2f} {} || Change 1h {:.3f}% || Change 24h: {:.3f}%`".format(
        elem['base'],
        float(elem["prices"]["latest"]),
        currency,
        float(elem["prices"]["latest_price"]["percent_change"]["hour"]) * 100,
        float(elem["prices"]["latest_price"]["percent_change"]["day"]) * 100,
    )


init_aliases()
