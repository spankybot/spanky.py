import inspect
import math
from spanky.plugin import hook
from spanky.plugin.event import EventType
from collections import OrderedDict, deque
from spanky.utils import discord_utils as dutils

MAX_ROWS = 10
LARROW=u'\U0001F448'
RARROW=u'\U0001F449'

SITEMS = [ \
    u'\U00000030\U0000FE0F\U000020E3', # zero
    u'\U00000031\U0000FE0F\U000020E3',
    u'\U00000032\U0000FE0F\U000020E3',
    u'\U00000033\U0000FE0F\U000020E3',
    u'\U00000034\U0000FE0F\U000020E3',
    u'\U00000035\U0000FE0F\U000020E3',
    u'\U00000036\U0000FE0F\U000020E3',
    u'\U00000037\U0000FE0F\U000020E3',
    u'\U00000038\U0000FE0F\U000020E3',
    u'\U00000039\U0000FE0F\U000020E3', # nine
    u'\U0001F1E6', # letter A
    u'\U0001F1E7',
    u'\U0001F1E8',
    u'\U0001F1E9',
    u'\U0001F1EA',
    u'\U0001F1EB',
    u'\U0001F1EC',
    u'\U0001F1ED',
    u'\U0001F1EE',
    u'\U0001F1EF',
    u'\U0001F1F0',
    u'\U0001F1F1',
    u'\U0001F1F2',
    u'\U0001F1F3',
    u'\U0001F1F4',
    u'\U0001F1F5',
    u'\U0001F1F6',
    u'\U0001F1F7',
    u'\U0001F1F8',
    u'\U0001F1F9',
    u'\U0001F1FA',
    u'\U0001F1FB',
    u'\U0001F1FC',
    u'\U0001F1FD',
    u'\U0001F1FE',
    u'\U0001F1FF'] # letter Z

posted_messages = deque(maxlen=50)

class Selector():
    def __init__(self, title, footer, async_send_message, call_dict, paged=False):
        self.async_send_message = async_send_message
        self.call_dict = call_dict
        self.msg_dict = {} # msg ID to (msg dict, emoji-func)
        self.paged = paged
        self.shown_page = 0
        self.total_pages = math.floor(len(call_dict) / MAX_ROWS) + 1

        # Initialize the embeds array in case there are multiple messages
        self.embeds = []

        # Populate embed item dict
        crt_idx = 0 # total emoji index
        #page_emoji_idx = 0 # per page emoji index

        emb_str = ""
        part_cnt = 1
        emoji_to_func = OrderedDict() # dict of emojis for current chunk
        for key, val in call_dict.items():
            # Get the current emoji
            crt_emoji = SITEMS[crt_idx]

            emoji_to_func[crt_emoji] = val
            emb_str += "%s %s\n" % (crt_emoji, key)

            crt_idx += 1

            # If more than MAX_ROWS items have been added split it
            if crt_idx >= MAX_ROWS:
                self.embeds.append(
                        (
                            dutils.prepare_embed(title="%s (part %d/%d)" % (title, part_cnt, self.total_pages), description=emb_str, footer_txt=footer),
                            emoji_to_func
                        )
                    )
                crt_idx = 0
                emb_str = ""
                part_cnt += 1
                emoji_to_func = {}

        if emb_str != "":
            # Add final split OR whole list
            if part_cnt > 1:
                self.embeds.append(
                        (
                            dutils.prepare_embed(title="%s (part %d/%d)" % (title, part_cnt, self.total_pages), description=emb_str, footer_txt=footer),
                            emoji_to_func
                        )
                    )
            else:
                self.embeds.append(
                        (
                            dutils.prepare_embed(title=title, description=emb_str, footer_txt=footer),
                            emoji_to_func
                        )
                    )

    def has_msg_id(self, msg_id):
        if msg_id in self.msg_dict:
            return True

        return False

    async def send_all_pages(self):
        for embed, emoji_to_func in self.embeds:
            # Send the message
            msg = await self.async_send_message(embed=embed, check_old=False)

            # Add it to the internal dict
            self.msg_dict[msg.id] = (msg, emoji_to_func)

            # Add all reacts
            for emoji in emoji_to_func.keys():
                await msg.async_add_reaction(emoji)

    async def send_one_page(self):
        embed, emoji_to_func = self.embeds[self.shown_page]

        # Send the message
        msg = await self.async_send_message(embed=embed, check_old=True)

        new_msg = False
        if msg.id not in self.msg_dict:
            new_msg = True

        # Add it to the internal dict so that we can quickly react to emotes
        self.msg_dict[msg.id] = (msg, emoji_to_func)

        if new_msg:
            if self.total_pages > 1:
                # If using pages, add arrows
                await msg.async_add_reaction(LARROW)
                await msg.async_add_reaction(RARROW)

            # Add all reacts
            for emoji in emoji_to_func.keys():
                await msg.async_add_reaction(emoji)

    async def do_send(self):
        # Add selector to posted messages
        posted_messages.append(self)

        if not self.paged:
            await self.send_all_pages()
        else:
            await self.send_one_page()

    async def handle_emoji(self, event):
        if event.msg.id not in self.msg_dict:
            return

        # Check if it's a page reaction
        if self.paged and \
            event.reaction.emoji.name in [LARROW, RARROW]:
            # If yes, increment decrement things
            if event.reaction.emoji.name == LARROW:
                self.shown_page -= 1
            elif event.reaction.emoji.name == RARROW:
                self.shown_page += 1

            # Check bounds
            if self.shown_page >= len(self.embeds):
                self.shown_page = 0
            elif self.shown_page < 0:
                self.shown_page = len(self.embeds) - 1

            # Send the new page
            await self.send_one_page()
            return

        # Get emoji to func map
        _, emoji_to_func = self.msg_dict[event.msg.id]

        # Check if emoji exists
        if event.reaction.emoji.name not in emoji_to_func:
            return

        # If it's an async function, await else just call
        if inspect.iscoroutinefunction(emoji_to_func[event.reaction.emoji.name]):
            await emoji_to_func[event.reaction.emoji.name](event)
        else:
            emoji_to_func[event.reaction.emoji.name](event)

@hook.event(EventType.reaction_add)
async def parse_react(bot, event):
    # Check if the reaction was made on a message that contains a selector
    found_selector = None
    for selector in posted_messages:
        if selector.has_msg_id(event.msg.id):
            found_selector = selector
            break

    if not found_selector:
        return

    # Handle the event
    await found_selector.handle_emoji(event)

    # Remove the reaction
    await event.msg.async_remove_reaction(event.reaction.emoji.name, event.author)

