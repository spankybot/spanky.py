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

from spanky.plugin import hook

API_URL = "https://api.coinmarketcap.com/v1/ticker/{}"

CURRENCY_SYMBOLS = {
    'USD': '$',
    'GBP': '£',
    'EUR': '€',
}


class Alias:
    def __init__(self, name, cmd, nocmd=True):
        self.name = name
        self.cmds = cmd
        self.nocmd = nocmd


ALIASES = (
    Alias('bitcoin', 'btc', False),
    Alias('litecoin', 'ltc', False),
    Alias('ethereum', 'eth', False),
    Alias('bitcoin-cash', 'bch'),
    Alias('ripple', 'xrp'),
    Alias('eos', 'eos'),
)


def get_request(ticker, currency):
    return requests.get(API_URL.format(quote_plus(ticker)), params={'convert': currency})


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
        globals()[_hook.__name__] = hook.command(alias.cmds, autohelp=False)(_hook)


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
        reply("Could not get value: {}".format(e))
        raise

    data = request.json()

    if "error" in data:
        return "{}.".format(data['error'])

    data = data[0]

    updated_time = datetime.fromtimestamp(float(data['last_updated']))
    if (datetime.today() - updated_time).days > 2:
        # the API retains data for old ticker names that are no longer updated
        # in these cases we just return a "not found" message
        return "Currency not found."

    currency_sign = CURRENCY_SYMBOLS.get(currency, '')

    try:
        converted_value = data['price_' + currency.lower()]
    except LookupError:
        return "Unable to convert to currency '{}'".format(currency)

    return "`{} || {}{:,.2f} {} - {:,.7f} BTC || Change 1h {}% || Change 24h: {}%`".format(
        data['symbol'], currency_sign, float(converted_value), currency.upper(),
        float(data['price_btc']), data["percent_change_1h"], data["percent_change_24h"]
    )


init_aliases()
