from spanky.plugin import hook
from spanky.utils import discord_utils as dutils

import requests
from requests.exceptions import RequestException

SEARCH_URL = "http://store.steampowered.com/api/storesearch/?term={}&l=english&cc=US"


class GameData:
    def __init__(self, data):
        self.data = data

    @property
    def name(self):
        return self.data["name"]

    @property
    def gid(self):
        return self.data["id"]

    @property
    def gid(self):
        return self.data["id"]

    @property
    def image(self):
        return self.data["tiny_image"]

    @property
    def metascore(self):
        if self.data["metascore"] != "":
            return self.data["metascore"]
        else:
            return "Unknown"

    @property
    def link(self):
        return f"https://store.steampowered.com/app/{self.gid}"

    @property
    def price(self):
        try:
            # Convert ":xxyy" to "xx.yy"
            price = self.data["price"]["final"]
            currency = self.data["price"]["currency"]

            return f"{price / 100} {currency}"
        except:
            return "Not found."


def search_steam(text):
    try:
        response = requests.get(SEARCH_URL.format(text))
    except RequestException:
        return "Exception searching for data."
    data = response.json()

    return [GameData(i) for i in data["items"]]


@hook.command()
async def steam(text, async_send_message):
    """
    <text or ID> - Search for a Steam game by name or ID.
    """
    items = []
    try:
        items = search_steam(text)
    except:
        return "Exception searching for data."

    if len(items) == 0:
        return "No results found."

    embed = dutils.prepare_embed(
        title="Steam data",
        description=f"Result for {text}",
        fields={
            "Name": items[0].name,
            "ID": items[0].gid,
            "Price": items[0].price,
            "Metascore": items[0].metascore,
            "Link": items[0].link,
        },
        inline_fields=True,
        image_url=items[0].image,
    )
    print(embed)

    await async_send_message(embed=embed)


@hook.command()
async def steamsearch(text, async_send_message):
    """
    <text> - Search steam for games.
    """
    items = []
    try:
        items = search_steam(text)
    except:
        return "Exception searching for data."

    if len(items) == 0:
        return "No results found."

    results = {}
    for item in items:
        results[item.name] = f"{item.link}"

    embed = dutils.prepare_embed(
        title="Steam search",
        description=f"Result for {text} - found {len(items)}",
        fields=results,
        inline_fields=False,
    )

    await async_send_message(embed=embed)
