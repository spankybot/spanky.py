import random

import requests
import aiohttp

import plugins.paged_content as paged
from spanky.plugin import hook
from spanky.utils import formatting


base_url = "http://api.urbandictionary.com/v0"
define_url = base_url + "/define"
random_url = base_url + "/random"


@hook.command(aliases=["ud"])
async def urban(text, reply, async_send_message):
    """urban <phrase> [id] -- Looks up <phrase> on urbandictionary.com."""

    headers = {"Referer": "http://m.urbandictionary.com"}

    page = {}
    async with aiohttp.ClientSession(raise_for_status=True) as session:
        if text:
            # clean and split the input
            text = text.lower().strip()
            parts = text.split()

            # fetch the definitions
            try:
                params = {"term": text}
                async with session.get(
                    define_url, params=params, headers=headers
                ) as resp:
                    page = await resp.json()
            except Exception as e:
                reply("Could not get definition: {}".format(e))

        else:
            # get a random definition!
            try:
                async with session.get(random_url, headers=headers) as resp:
                    page = await resp.json()
            except Exception as e:
                reply("Could not get definition: {}".format(e))

    definitions = page["list"]

    defs = []
    for definition in definitions:
        def_text = " ".join(definition["definition"].split())
        def_text = formatting.truncate(def_text, 400)

        name = definition["word"]
        url = definition["permalink"]
        output = "%s: %s - <%s>" % (name, def_text, url)
        defs.append(output)

    if len(defs) == 0:
        reply("No definition found")

    content = paged.element(
        text_list=defs,
        send_func=async_send_message,
        max_lines=1,
        max_line_len=2000,
        no_timeout=True,
        with_quotes=False,
    )

    await content.get_crt_page()
