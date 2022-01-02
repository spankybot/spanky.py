from plugins.steam import SEARCH_URL
from spanky.plugin import hook
from spanky.utils import discord_utils as dutils

import requests
import re

from bs4 import BeautifulSoup

SEARCH_URL = "https://www.goodreads.com/search?q={}"

# Goodreads doesn't have an API, so parse HTML crap


class BookDataSearch:
    """
    Book data returned from a search.
    """

    def __init__(self, data):
        self.data = data

    @property
    def title(self):
        return self.data.find("a").get("title")

    @property
    def link(self):
        link = self.data.find("a").get("href")
        # Cut "from_search"
        pos = link.find("?from_search")

        return "https://www.goodreads.com" + link[:pos]


class BookData:
    """
    Book data returned from a search.
    """

    def __init__(self, data, link):
        self.data = data
        self.book_link = link

    @property
    def title(self):
        return self.data.title.get_text()

    @property
    def rating(self):
        try:
            return self.data.find("span", {"itemprop": "ratingValue"}).get_text()
        except:
            print(self.data)
            return "Could not fetch rating."

    @property
    def link(self):
        return self.book_link

    @property
    def cover(self):
        try:
            return self.data.find("div", {"class": "editionCover"}).find("img")["src"]
        except:
            return ""

    @property
    def description(self):
        try:
            text = self.data.find(
                "span", {"id": re.compile("freeText.*"), "style": "display:none"}
            ).get_text()
            if len(text) > 1024:
                text = text[:1020] + "..."

            return text
        except:
            return "Could not fetch description."


def search(text):
    """
    Search for multiple books.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:15.0) Gecko/20100101 Firefox/15.0.1",
    }
    response = requests.get(SEARCH_URL.format(text), headers=headers)

    bf = BeautifulSoup(response.content, "html.parser")
    books = bf.find_all("tr", {"itemtype": "http://schema.org/Book"})

    return [BookDataSearch(i) for i in books]


def getbook(link):
    """
    Search for one book.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:15.0) Gecko/20100101 Firefox/15.0.1",
    }
    response = requests.get(link, headers=headers)

    bf = BeautifulSoup(response.content, "html.parser")
    return BookData(bf, link)


@hook.command()
async def goodreads_search(text, async_send_message):
    """
    <text> - Search for books on Goodreads.
    """
    items = []
    try:
        items = search(text)
    except Exception as e:
        return "Exception searching for data: " + str(e)

    if len(items) == 0:
        return "No results found."

    results = {}
    for item in items:
        results[item.title] = item.link

    embed = dutils.prepare_embed(
        title="Goodreads search",
        description=f"Result for {text}",
        fields=results,
        inline_fields=False,
    )

    await async_send_message(embed=embed)


@hook.command()
async def goodreads(text, async_send_message):
    """
    <text> - List first goodreads result.
    """
    # Do a search first
    try:
        items = search(text)
    except Exception as e:
        return "Exception searching for data: " + str(e)

    if len(items) == 0:
        return "No results found."

    # Go to the first result
    item = None
    try:
        item = getbook(items[0].link)
    except Exception as e:
        return "Exception searching for data: " + str(e)

    if item == None:
        return "No results found."

    embed = dutils.prepare_embed(
        title="Goodreads book",
        description=f"Result for {text}",
        fields={
            "Title": item.title,
            "Rating": item.rating,
            "Link": item.link,
            "Description": item.description,
        },
        image_url=item.cover,
        inline_fields=False,
    )

    await async_send_message(embed=embed)
