import urllib.parse

import requests
import requests.exceptions
from bs4 import BeautifulSoup

from spanky.plugin import hook


@hook.command("down")
def down(text):
    """<url> - checks if <url> is online or offline
    :type text: str
    """

    if "://" not in text:
        text = 'http://' + text

    text = 'http://' + urllib.parse.urlparse(text).netloc

    try:
        r = requests.get(text)
        r.raise_for_status()
    except requests.exceptions.ConnectionError:
        return '{} seems to be down'.format(text)
    else:
        return '{} seems to be up'.format(text)


@hook.command()
def isup(text):
    """<url> - uses isup.me to check if <url> is online or offline
    :type text: str
    """
    url = text.strip()

    # slightly overcomplicated, esoteric URL parsing
    scheme, auth, path, query, fragment = urllib.parse.urlsplit(url)

    domain = auth or path

    try:
        response = requests.get('http://isup.me/' + domain)
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        return "Failed to get status."
    if response.status_code != requests.codes.ok:
        return "Failed to get status."

    soup = BeautifulSoup(response.text, 'lxml')

    content = soup.find('div').text.strip()

    if "not just you" in content:
        return "It's not just you. {} looks down from here!".format(url)
    elif "is up" in content:
        return "It's just you. {} is up.".format(url)
    else:
        return "Huh? That doesn't look like a site on the interweb."
