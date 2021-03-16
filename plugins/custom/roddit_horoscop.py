from spanky.plugin import hook
import requests
from bs4 import BeautifulSoup
import spanky.utils.discord_utils as dutils
from unidecode import unidecode

SERVERS = [
    "648937029433950218",  # CNC test server
    "297483005763780613",  # plp test server
    "287285563118190592",  # Roddit
    "754550072955371620"  # tz srv
]

URL = "https://horoscop.ro/%s"


@hook.command(server_id=SERVERS, format="zodie")
async def horoscop(text, reply, async_send_message):
    """
    horoscop <zodie> - Afișează horoscopul unei zodii
    """
    r = requests.get(URL % unidecode(text.lower()))
    bf = BeautifulSoup(r.content, "html.parser")
    body = bf.find('div', {'class': 'zodie-content-texts black'})
    if body == None:
        reply("N-am găsit zodia")
        return

    header = bf.find('div', {'class': 'big-title'})

    em = dutils.prepare_embed(title=header.text, description=body.text)
    await async_send_message(embed=em)
