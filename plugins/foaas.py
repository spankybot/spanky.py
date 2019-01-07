import json
import random
from pathlib import Path

import requests

from spanky.plugin import hook

BASE_URL = "http://www.foaas.com/{fuck}/{target}"

headers = {'Accept': 'text/plain'}

fuck_offs = {}


def format_url(fucker, fuckee=None):
    if fuckee:
        fucks = fuck_offs['fuck_offs']
        target = "{fuckee}/{fucker}".format(fuckee=fuckee, fucker=fucker)
    else:
        fucks = fuck_offs['single_fucks']
        target = fucker

    return BASE_URL.format(fuck=random.choice(fucks), target=target)


def get_fuck_off(fucker, fuckee):
    url = format_url(fucker, fuckee)
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.text


@hook.on_start
def load_fuck_offs():
    fuck_offs.clear()
    data_file = Path("plugin_data/foaas.json")
    with data_file.open(encoding='utf-8') as f:
        fuck_offs.update(json.load(f))


@hook.command()
def fuckoff(text, event):
    """[name] - tell some one to fuck off or just .fos for a generic fuckoff"""
    out = get_fuck_off(event.author.name, text)
    return out
