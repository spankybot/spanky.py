from urllib.parse import quote_plus

import requests

from spanky.plugin import hook

BASE_URL = "http://query.yahooapis.com/v1/public/yql"
ENV = "http://datatables.org/alltables.env"


def get_data(symbol):
    query = 'SELECT * FROM yahoo.finance.quote WHERE symbol="{}" LIMIT 1'.format(quote_plus(symbol))
    request = requests.get(BASE_URL, params={'q': query, 'env': ENV, 'format': 'json'})
    request.raise_for_status()

    return request.json()['query']


@hook.command()
def stock(text, reply):
    """<symbol> -- gets stock information"""
    sym = text.strip()

    try:
        data = get_data(text)
    except requests.exceptions.HTTPError as e:
        reply("Could not get stock data: {}".format(e))
        raise

    if not data["results"]:
        return "No results."

    quote = data['results']['quote']

    # if we don't get a company name back, the symbol doesn't match a company
    if quote['Change'] is None:
        return "Unknown ticker symbol: {}".format(sym)

    change = float(quote['Change'])
    price = float(quote['LastTradePriceOnly'])

    # this is for dead companies, if this isn't here PercentChange will fail with DBZ
    if price == 0 and change == 0:
        return "{Name} ({symbol}) - {LastTradePriceOnly}".format(**quote)

    if change < 0:
        quote['color'] = "5"
    else:
        quote['color'] = "3"

    quote['PercentChange'] = 100 * change / (price - change)

    return "{Name} ({symbol}): {LastTradePriceOnly} " \
           "{color}{Change} ({PercentChange:.2f}%) " \
           "- Day Range: {DaysRange} " \
           "MCAP: {MarketCapitalization}".format(**quote)
