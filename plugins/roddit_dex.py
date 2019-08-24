from spanky.plugin import hook
import asyncio
import sys
import requests
import os
import plugins.paged_content as paged
from bs4 import BeautifulSoup

RODDIT_ID = "287285563118190592"
TESTOSTERON = "611894947024470027"

@hook.command(server_id=[RODDIT_ID, TESTOSTERON])
async def dex(send_message, async_send_message, text):
    """<cuvant> - Cauta definitia pentru un cuvant in DEX"""
    r = requests.get('https://dexonline.ro/definitie/%s/expandat' % text)
    bf = BeautifulSoup(r.content, "html.parser")
    results = bf.find_all('div', {'class' : 'defWrapper'})

    if len(results) == 0:
        send_message("n-am gasit boss")
        return

    content = []
    for i in range(len(results)):
        content.append(results[i].find_all('span', {'class' : 'def'})[0].text)

    paged_content = paged.element(content, async_send_message, "Definitii pentru %s" % text, max_lines=1, max_line_len=1800)
    await paged_content.get_crt_page()
