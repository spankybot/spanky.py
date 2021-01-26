from spanky.plugin import hook
from webull import webull

wb = webull()

filter_fields = [
    "name", "symbol", "exchangeCode", "close", "change", "pPrice", "pChange", "open", "low", "high"
]

@hook.command()
def stock(text):
    return quote(text)

@hook.command()
def quote(text):
    try:
        data = wb.get_quote(text)
    except ValueError as e:
        return str(e)

    return "`{symbol}: {price} {currency} || Open: {open}, Close: {close}, High: {high}, Low: {low} || Change: {change}%`".format(
        symbol=data["symbol"],
        price=data["pPrice"],
        currency=data["currencyCode"],
        open=data["open"],
        close=data["close"],
        high=data["high"],
        low=data["low"],
        change=data["pChange"]
    )

@hook.command()
def dquote(text, send_embed):
    try:
        data = wb.get_quote(text)
    except ValueError as e:
        return str(e)

    to_send = {}
    for field in sorted(filter_fields):
        to_send[field] = data[field]

    to_send["link"] = f"https://www.marketwatch.com/investing/stock/{text}"

    return send_embed(text, "", to_send)