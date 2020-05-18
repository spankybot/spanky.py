from spanky.plugin import hook
from collections import deque
from googleapiclient.discovery import build
from spanky.utils import discord_utils as dutils
from spanky.plugin.event import EventType

LARROW=u'\U0001F448'
RARROW=u'\U0001F449'
dev_key = None
dev_cx = None
search_results = deque(maxlen=50)

class GISResult():
    def __init__(self, urls, async_send_message, search_term, event):
        self.urls = urls
        self.async_send_message = async_send_message
        self.crt_page = 0
        self.msg = None

        self.search_term = search_term
        self.footer = "Search author: %s" % event.author.name

        search_results.append(self)

    async def send_msg(self):
        self.embed = dutils.prepare_embed(
            title="Image search",
            description="Query: %s (result %d/%d)" % (self.search_term, self.crt_page + 1, len(self.urls)),
            image_url=self.urls[self.crt_page],
            footer_txt=self.footer)

        new_message = self.msg
        self.msg = await self.async_send_message(embed=self.embed)

        if new_message is None:
            await self.msg.async_add_reaction(LARROW)
            await self.msg.async_add_reaction(RARROW)

    async def handle_emoji(self, event):
        # Check if arrow left or right
        if event.reaction.emoji.name == LARROW:
            self.crt_page -= 1
        elif event.reaction.emoji.name == RARROW:
            self.crt_page += 1

        # Check bounds
        if self.crt_page >= len(self.urls):
            self.crt_page = 0
        elif self.crt_page < 0:
            self.crt_page = len(self.urls) - 1

        await self.send_msg()

@hook.on_start()
def load_key(bot):
    global dev_key
    global dev_cx

    dev_key = bot.config.get("api_keys", {}).get("google_dev_key", None)
    dev_cx = bot.config.get("api_keys", {}).get("google_cx", None)

@hook.command()
async def gis(text, async_send_message, event):
    """<query> - Search for a image."""
    service = build("customsearch", "v1", developerKey=dev_key)

    res = service.cse().list(
        q=text,
        safe="active",
        cx=dev_cx,
        ).execute()

    urls = []
    for img in res.get("items", []):
        if "cse_image" in img["pagemap"].keys():
            urls.append(img["pagemap"]["cse_image"][0]["src"])

    if len(urls) == 0:
        return "No results found"

    await GISResult(urls, async_send_message, text, event).send_msg()

@hook.event(EventType.reaction_add)
async def parse_react(bot, event):
    # Check if the reaction was made on a message that contains a search result
    found = None
    for res in search_results:
        if res.msg.id == event.msg.id:
            found = res
            break

    if not found:
        return

    # Handle the event
    await found.handle_emoji(event)

    # Remove the reaction
    await event.msg.async_remove_reaction(event.reaction.emoji.name, event.author)
