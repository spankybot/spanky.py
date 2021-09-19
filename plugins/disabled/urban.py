import random

import requests

import plugins.paged_content as paged
from spanky.plugin import hook
from spanky.utils import formatting


base_url = "http://api.urbandictionary.com/v0"
define_url = base_url + "/define"
random_url = base_url + "/random"


@hook.command()
async def urban(text, reply, async_send_message):
    """urban <phrase> [id] -- Looks up <phrase> on urbandictionary.com."""

    headers = {"Referer": "http://m.urbandictionary.com"}

    if text:
        # clean and split the input
        text = text.lower().strip()
        parts = text.split()

        # fetch the definitions
        try:
            params = {"term": text}
            request = requests.get(define_url, params=params, headers=headers)
            request.raise_for_status()
        except (
            requests.exceptions.HTTPError,
            requests.exceptions.ConnectionError,
        ) as e:
            reply("Could not get definition: {}".format(e))

        page = request.json()
    else:
        # get a random definition!
        try:
            request = requests.get(random_url, headers=headers)
            request.raise_for_status()
        except (
            requests.exceptions.HTTPError,
            requests.exceptions.ConnectionError,
        ) as e:
            reply("Could not get definition: {}".format(e))

        page = request.json()

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
