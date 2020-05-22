import inspect
from spanky.plugin import hook
from spanky.plugin.event import EventType
from collections import OrderedDict, deque
from spanky.utils import discord_utils as dutils
from spanky.utils import time_utils as tutils


MAX_ROWS = 10  # Max rows per page
LARROW = "\U0001F448"
RARROW = "\U0001F449"

MIN_SEC = 3  # Min seconds between assignments
MSG_TIMEOUT = 3  # Timeout after which the message dissapears
last_user_assign = {}  # Dict to check for user spamming buttons

SITEMS = [
    "\U00000030\U0000FE0F\U000020E3",  # zero
    "\U00000031\U0000FE0F\U000020E3",
    "\U00000032\U0000FE0F\U000020E3",
    "\U00000033\U0000FE0F\U000020E3",
    "\U00000034\U0000FE0F\U000020E3",
    "\U00000035\U0000FE0F\U000020E3",
    "\U00000036\U0000FE0F\U000020E3",
    "\U00000037\U0000FE0F\U000020E3",
    "\U00000038\U0000FE0F\U000020E3",
    "\U00000039\U0000FE0F\U000020E3",  # nine
    "\U0001F1E6",  # letter A
    "\U0001F1E7",
    "\U0001F1E8",
    "\U0001F1E9",
    "\U0001F1EA",
    "\U0001F1EB",
    "\U0001F1EC",
    "\U0001F1ED",
    "\U0001F1EE",
    "\U0001F1EF",
    "\U0001F1F0",
    "\U0001F1F1",
    "\U0001F1F2",
    "\U0001F1F3",
    "\U0001F1F4",
    "\U0001F1F5",
    "\U0001F1F6",
    "\U0001F1F7",
    "\U0001F1F8",
    "\U0001F1F9",
    "\U0001F1FA",
    "\U0001F1FB",
    "\U0001F1FC",
    "\U0001F1FD",
    "\U0001F1FE",
    "\U0001F1FF",
]  # letter Z

posted_messages = deque(maxlen=50)


class Selector:
    def __init__(self, title, footer, call_dict, paged=False):
        self.msg_dict = {}  # msg ID to (msg dict, emoji-func)
        self.paged = paged
        self.shown_page = 0
        self.title = title
        self.footer = footer

        self.set_items(call_dict)

    def set_items(self, call_dict):
        self.total_pages = len(call_dict) // MAX_ROWS + int(
            len(call_dict) % MAX_ROWS != 0
        )

        # Initialize the embeds array in case there are multiple messages
        self.embeds = []

        # Populate embed item dict
        crt_idx = 0  # total emoji index
        emb_str = ""  # embed string per page
        part_cnt = 1  # page count
        emoji_to_func = OrderedDict()  # dict of emojis for current chunk

        for key, val in call_dict.items():
            # Get the current emoji
            crt_emoji = SITEMS[crt_idx]

            emoji_to_func[crt_emoji] = (val, key)  # emoji -> (function, label)
            emb_str += "%s %s\n" % (crt_emoji, key)

            crt_idx += 1

            # If more than MAX_ROWS items have been added split it
            if crt_idx >= MAX_ROWS:
                self.embeds.append(
                    (
                        dutils.prepare_embed(
                            title="%s (part %d/%d)"
                            % (self.title, part_cnt, self.total_pages),
                            description=emb_str,
                            footer_txt=self.footer,
                        ),
                        emoji_to_func,
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
                        dutils.prepare_embed(
                            title="%s (part %d/%d)"
                            % (self.title, part_cnt, self.total_pages),
                            description=emb_str,
                            footer_txt=self.footer,
                        ),
                        emoji_to_func,
                    )
                )
            else:
                self.embeds.append(
                    (
                        dutils.prepare_embed(
                            title=self.title,
                            description=emb_str,
                            footer_txt=self.footer,
                        ),
                        emoji_to_func,
                    )
                )

    def has_msg_id(self, msg_id):
        if msg_id in self.msg_dict:
            return True

        return False

    async def send_all_pages(self, event):
        for embed, emoji_to_func in self.embeds:
            # Send the message
            msg = await event.async_send_message(embed=embed, check_old=False)

            # Add it to the internal dict
            self.msg_dict[msg.id] = (msg, emoji_to_func)

            # Add all reacts
            for emoji in emoji_to_func.keys():
                await msg.async_add_reaction(emoji)

    async def send_one_page(self, event):
        embed, emoji_to_func = self.embeds[self.shown_page]
        # Send the message
        msg = await event.async_send_message(embed=embed, check_old=True)

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

    async def do_send(self, event):
        # Add selector to posted messages
        posted_messages.append(self)

        if not self.paged:
            await self.send_all_pages(event)
        else:
            await self.send_one_page(event)

    async def handle_emoji(self, event):
        if event.msg.id not in self.msg_dict:
            return

        # Check if it's a page reaction
        if self.paged and event.reaction.emoji.name in [LARROW, RARROW]:
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
        await self.send_one_page(event)

        # Get emoji to func map
        _, emoji_to_func = self.msg_dict[event.msg.id]

        # Check if emoji exists
        if event.reaction.emoji.name not in emoji_to_func:
            return

        # If it's an async function, await else just call
        target_func, label = emoji_to_func[event.reaction.emoji.name]
        try:
            if inspect.iscoroutinefunction(target_func):
                await target_func(event, label)
            else:
                target_func(event, label)
        except:
            import traceback

            traceback.print_exc()


class RoleSelector(Selector):
    # If N seconds have passed since the last role update, check the server status
    ROLE_UPDATE_INTERVAL = 60

    def __init__(self, server, roles, title, max_selectable, paged):
        super().__init__(
            title=title,
            footer=f"Max selectable: {max_selectable if max_selectable > 0 else 'Unlimited' }",
            call_dict={},
            paged=paged,
        )
        self.server = server
        self.roles = roles
        self.max_selectable = max_selectable
        self.last_role_update = 0

        self.update_role_list()

    def update_role_list(self):
        # Check if we need to get the roles
        if tutils.tnow() - self.last_role_update > RoleSelector.ROLE_UPDATE_INTERVAL:
            # Get the roles
            roles = dutils.get_roles_from_ids(self.roles, self.server)

            self.name_to_role = {}  # Map names to roles for quick lookup
            role_list = list()
            for role in roles:
                self.name_to_role[role] = roles[role]
                role_list.append(role)

            role_list = sorted(list(role_list), key=str.lower)

            role_dict = OrderedDict()  # Role list to pass to the selector
            for item in role_list:
                role_dict[item] = self.do_stuff

            # Mark last role update time
            self.last_role_update = tutils.tnow()

            # Set the items
            self.set_items(role_dict)

    async def handle_emoji(self, event):
        # Before handling an emoji, update the role list
        self.update_role_list()

        await super().handle_emoji(event)

    async def do_stuff(self, event, label):
        # Check role assign spam
        now = tutils.tnow()
        if (
            event.author.id in last_user_assign
            and now - last_user_assign[event.author.id] < MIN_SEC
        ):
            last_user_assign[event.author.id] = now
            event.author.send_pm(
                "You're assigning roles too quickly. You need to wait %d seconds between assignments"
                % MIN_SEC
            )
            return

        print("Assign %s" % label)
        the_role = self.name_to_role[label]
        last_user_assign[event.author.id] = now

        crt_roles = dutils.user_roles_from_list(
            event.author, self.name_to_role.values()
        )
        # Check if the user already has the role so that we remove it
        for crt in crt_roles:
            if the_role.id == crt.id:
                event.author.remove_role(the_role)
                await event.async_send_message(
                    "<@%s>: `Removed: %s`" % (event.author.id, the_role.name),
                    timeout=MSG_TIMEOUT,
                    check_old=False,
                )
                return

        # Remove extra roles
        removed = []
        if self.max_selectable > 0 and len(crt_roles) >= self.max_selectable:
            # +1 to make room for another
            for i in range(len(crt_roles) - self.max_selectable + 1):
                event.author.remove_role(crt_roles[i])
                removed.append(crt_roles[i].name)

        event.author.add_role(the_role)
        reply_msg = "Added: %s" % the_role.name
        if len(removed) > 0:
            reply_msg += " || Removed: %s" % ", ".join(removed)
        await event.async_send_message(
            "<@%s>: `%s`" % (event.author.id, reply_msg),
            timeout=MSG_TIMEOUT,
            check_old=False,
        )


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
