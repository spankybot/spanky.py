import re

import requests

from spanky.plugin import hook

id_re = re.compile("tt\d+")

@hook.command
def imdb(text, bot):
    """<movie> - gets information about <movie> from IMDb"""

    headers = {'User-Agent': bot.user_agent}
    strip = text.strip()

    if id_re.match(strip):
        endpoint = 'title'
        params = {'id': strip}
    else:
        endpoint = 'search'
        params = {'q': strip, 'limit': 1}

    request = requests.get(
        "https://imdb-scraper.herokuapp.com/" + endpoint,
        params=params,
        headers=headers)
    request.raise_for_status()
    content = request.json()

    if content['success'] is False:
        return 'Unknown error'
    elif len(content['result']) == 0:
        return 'No movie found'
    else:
        result = content['result']
        if endpoint == 'search':
            result = result[0]  # part of the search results, not 1 record
        url = 'http://www.imdb.com/title/{}'.format(result['id'])
        return movie_str(result) + ' ' + url

def movie_str(movie):
    movie['genre'] = ', '.join(movie['genres'])
    out = '\x02%(title)s\x02 (%(year)s) (%(genre)s): %(plot)s'
    if movie['runtime'] != 'N/A':
        out += ' \x02%(runtime)s\x02.'
    if movie['rating'] != 'N/A' and movie['votes'] != 'N/A':
        out += ' \x02%(rating)s/10\x02 with \x02%(votes)s\x02' \
               ' votes.'
    return out % movie
