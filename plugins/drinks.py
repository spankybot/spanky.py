import json
import os
import random

from spanky.plugin import hook
from spanky.utils import web

drinks = None

@hook.on_start
def load_drinks(bot):
    """load the drink recipes"""
    global drinks
    with open(os.path.join("plugin_data/drinks.json")) as json_data:
        drinks = json.load(json_data)


@hook.command()
def drink(text):
    """<nick> - makes the user a random cocktail."""
    index = random.randint(0, len(drinks) - 1)
    drink = drinks[index]['title']
    url = web.try_shorten(drinks[index]['url'])
    if drink.endswith(' recipe'):
        drink = drink[:-7]
    contents = drinks[index]['ingredients']
    out = "grabs some"
    for x in contents:
        if x == contents[len(contents) - 1]:
            out += " and {}".format(x)
        else:
            out += " {},".format(x)
    out += " and makes {} a(n) {}. {}".format(text, drink, url)
    return out
