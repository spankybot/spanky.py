from spanky.plugin import hook
import requests
from bs4 import BeautifulSoup
import spanky.utils.discord_utils as dutils
from unidecode import unidecode

SERVERS = [
    "648937029433950218", # CNC test server
    "297483005763780613", # plp test server
    "287285563118190592"  # Roddit
]

URL = "https://www.eastrolog.ro/horoscop-zilnic/horoscop-%s.php"

# we need to spoof the user agent, or else we get 403 forbidden from the website
headers = {
    "User-Agent": "Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:83.0) Gecko/20100101 Firefox/83.0"
}
@hook.command(server_id=SERVERS, format="zodie")
async def horoscop(text, reply, async_send_message):
    """
    horoscop <zodie> - Afișează horoscopul unei zodii
    """
    text = unidecode(text.lower())
    r = requests.get(URL % text, headers=headers)
    bf = BeautifulSoup(r.content, "html.parser")
    result = bf.find('div', {'class': 'contentLining'})
    if result == None:
        reply("N-am găsit zodia")
        return

    context = result.find('figcaption')
    header = result.find('div', {'class': 'psh2'})
    body = result.find('p')
    
    em = dutils.prepare_embed(title=header.text, description=body.text, footer_txt=context.text)
    
    await async_send_message(embed=em)
