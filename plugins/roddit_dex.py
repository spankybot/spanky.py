from spanky.plugin import hook
import asyncio
import sys
import requests
import os
from bs4 import BeautifulSoup

RODDIT_ID = "287285563118190592"

@hook.command(server_id=RODDIT_ID)
def dex(send_message, text):
    """<cuvant> - Cauta definitia pentru un cuvant in DEX"""

    def_nr = 0
    stext = text.split()

    r = requests.get('https://dexonline.ro/definitie/%s/expandat' % stext[0])
    bf = BeautifulSoup(r.content, "html.parser")
    letters = bf.find_all('div', {'class' : 'defWrapper'})

    if len(stext) > 1:
        try:
            def_nr = int(stext[1])
        except:
            return
        if def_nr < 0 or def_nr >= len(letters):
            send_message("Cifra trebuie sa fie in [0, %d]" % (len(letters) - 1))
            return

    if len(letters) == 0:
        send_message("n-am gasit boss")
        return

    msg = letters[def_nr].find_all('span', {'class' : 'def'})[0].text

    send_message(msg)
    if len(stext) == 1 and len(letters) > 1:
        send_message("Sau inca %d definitii disponibile. (.dex cuvant nr_definitie)" % (len(letters) - 1))
