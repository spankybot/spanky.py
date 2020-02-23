import os
import random

import requests
from bs4 import BeautifulSoup

from spanky.plugin import hook

search_url = "https://www.dogpile.com/search"

CERT_PATH = 'dogpile.crt'
HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux i586; rv:31.0) Gecko/20100101 Firefox/73.0"
}

session = requests.Session()


@hook.on_start
def check_certs(bot):
    try:
        with requests.get(search_url):
            pass
    except requests.exceptions.SSLError:
        session.verify = os.path.join(str(bot.data_dir), CERT_PATH)
    else:
        session.verify = None


def query(endpoint, text):
    params = {'q': " ".join(text.split())}
    with requests.get(
            search_url + "/" + endpoint, params=params, headers=HEADERS,
            verify=session.verify
    ) as r:
        r.raise_for_status()
        return BeautifulSoup(r.content)


@hook.command()
def gis(text):
    """<query> - Uses the dogpile search engine to search for images."""
    soup = query('images', text)
    results_container = soup.find('div', {'class': 'images-bing__list'})
    if not results_container:
        return "No results found."

    results_list = results_container.find_all('div', {'class': 'image'})
    if not results_list:
        return "No results found."

    image = random.choice(results_list)
    return image.find('a', {'class': 'link'})['href']


@hook.command()
def g(text):
    """<query> - Uses the dogpile search engine to find shit on the web."""
    soup = query('web', text)
    results = soup.find_all('div', {'class': 'web-bing__result'})
    if not results:
        return "No results found."

    result = results[0]
    result_url = result.find('span', {'class': 'web-bing__url'}).text
    result_description = result.find('span', {'class': 'web-bing__description'}).text
    return "{} -- {}".format(result_url, result_description)
