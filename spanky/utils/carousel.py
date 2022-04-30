import enum
import inspect
from collections import OrderedDict, deque
from typing import TYPE_CHECKING, Optional
from spanky.utils import discord_utils as dutils
from spanky.utils import time_utils as tutils

from spanky.inputs.nextcord import EventReact
from spanky.hook2.event import EventType

from spanky.hook2 import Hook

if TYPE_CHECKING:
    from spanky.bot import Bot
    from spanky.inputs.nextcord import Channel, Server

MAX_ROWS = 10  # Max rows per page
LARROW = "\U0001F448"
RARROW = "\U0001F449"

MIN_SEC = 1  # Min seconds between assignments
MSG_TIMEOUT = 2  # Timeout after which the message dissapears
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


class SelectorType(enum.Enum):
    TEMPORARY = "temporary"
    PERMANENT = "permanent"


class Selector:
    # Calls the storage notifier to reserialize the selector
    # Avoids multi-page selectors losing the current page
    # when the bot is reset.
    _storage_notifier = None

    _selector_loader = None

    _permanent_selectors = {}
    _temporary_selectors = deque(maxlen=100)

    def __init__(
        self,
        title,
        footer,
        call_dict,
        server: "Server",
        channel: "Channel",
        max_rows=10,
        hook: Optional[Hook] = None,
        selector_type: SelectorType = SelectorType.TEMPORARY,
    ):
        self.shown_page = 0
        self.title = title
        self.footer = footer
        self.msg = None
        self.max_rows = max_rows

        self.hook = hook
        self.selector_type = selector_type

        self.server = server
        self.channel = channel

        self.call_dict = call_dict
        self.crt_emoji_to_func = {}

        self.set_items(self.call_dict)

    def set_items(self, call_dict):
        self.total_pages = len(call_dict) // self.max_rows + int(
            len(call_dict) % self.max_rows != 0
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

            # If more than self.max_rows items have been added split it
            if crt_idx >= self.max_rows:
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
        if not self.msg:
            return False

        return msg_id == self.msg.id

    def get_msg_id(self):
        """
        Returns all message IDs
        """
        if not self.msg:
            return None

        return self.msg.id

    async def add_emojis(self):
        if self.shown_page > len(self.embeds):
            self.shown_page = 0
        if len(self.embeds) == 0:
            return
        _, emoji_to_func = self.embeds[self.shown_page]

        if self.total_pages > 1:
            # If using pages, add arrows
            await self.msg.async_add_reaction(LARROW)
            await self.msg.async_add_reaction(RARROW)

        # Add all reacts
        for emoji in emoji_to_func.keys():
            await self.msg.async_add_reaction(emoji)

    def build_emoji_lookup(self):
        """
        Builds the emoji lookup table.
        """
        try:
            _, emoji_to_func = self.embeds[self.shown_page]
            self.crt_emoji_to_func = emoji_to_func
        except:
            import traceback
            traceback.print_exc()

    async def send_one_page(self, event):
        embed, _ = self.embeds[self.shown_page]

        new_msg = False
        print("send one page 1")
        # Send the message
        if not self.msg:
            self.msg = await event.async_send_message(embed=embed, check_old=True)
            new_msg = True
            print("send one page 2.1")
        else:
            await event.async_edit_message(msg=self.msg, embed=embed)
            print("send one page 2.2")

        # Build emoji lookup table
        self.build_emoji_lookup()

        if new_msg:
            await self.add_emojis()

        print("send one page 3")
        # Notify the storage that page has changed
        if Selector._storage_notifier:
            Selector._storage_notifier(event.server, self)
        print("send one page 4")

    async def reset_reacts(self, bot):
        await self.msg.clear_reactions()
        await self.add_emojis()

    async def do_send(self, event):
        await self.send_one_page(event)
        self.register_selector()

    # Temporary/Permanent selector handling
    def register_selector(self):
        if not self.msg:
            raise Exception("Trying to register unsent selector")

        if self.selector_type == SelectorType.TEMPORARY:
            self.hook.add_temporary_msg_react(self.msg.id, self.handle_react)
            Selector._temporary_selectors.append(self)

        elif self.selector_type == SelectorType.PERMANENT:
            self.hook.add_permanent_msg_react(self.msg.id, self.handle_react)
            Selector._permanent_selectors[self.msg.id] = self

        else:
            print("WARNING: Unknown selector type:", self.selector_type)

    # Upgrade temporary selector to a permanent one
    def upgrade_selector(self):
        if not self.msg:
            raise Exception("Trying to register unsent selector")
        if self.selector_type == SelectorType.PERMANENT:
            print("Trying to upgrade permanent selector to permanent. Skipping")
            return
        self.selector_type = SelectorType.PERMANENT
        self.hook.add_permanent_msg_react(self.msg.id, self.handle_react)

    # serialize serializes the carousel-specific data.
    # Subclasses should call this and then add their specific info
    def serialize(self) -> dict:
        data = {}
        data["server_id"] = self.server.id
        data["channel_id"] = self.channel.id
        data["msg_id"] = self.get_msg_id()
        data["shown_page"] = self.shown_page
        data["selector_type"] = self.selector_type.value
        return data

    @staticmethod
    def get_server_chan(bot: "Bot", data: dict):
        server = bot.get_server(data["server_id"])
        if not server:
            print("Could not find server id %s" % data["server_id"])
            return None, None

        chan = server.get_chan(data["channel_id"])
        if not chan:
            print("Could not find selector channel %s" % data["channel_id"])
            return server, None

        return server, chan

    async def scan_reacts(self, bot, msg, force_update = False):

        if force_update:
            msg = await self.channel.async_get_message(msg.id)
            self.msg = msg

        # Act on dangling reacts
        for react in msg.reactions():
            if react.emoji.name in self.crt_emoji_to_func.keys() or react.emoji.name in [LARROW, RARROW]:
                async for user in react.users():
                    # Build the react
                    event = EventReact(EventType.reaction_add, user._raw, react._raw)
                    if user.id == bot.get_own_id():
                        continue

                    await self.handle_react(event)

    # Deserialization common core
    async def finish_deserialize(self, bot: "Bot", data: dict, event):
        # Set selector page
        self.shown_page = data["shown_page"]

        if "selector_type" in data:
            self.selector_type = SelectorType(data["selector_type"])

        # Rebuild message cache
        msg_id = data["msg_id"]

        # Get the saved message and set it
        msg = await self.channel.async_get_message(msg_id)
        if not msg:
            return None
        self.msg = msg

        # Add message to backend cache
        bot.backend.add_msg_to_cache(msg)

        # Build the emoji lookup table
        #self.set_items(self.call_dict)
        self.build_emoji_lookup()

        await self.scan_reacts(bot, msg)

        # Remove reacts from other people
        #await self.reset_reacts(bot)

        # Register the react handler
        self.register_selector()

    @staticmethod
    async def deserialize(bot: "Bot", data: dict, hook: Hook, event) -> Optional["Selector"]:
        raise NotImplementedError()

    async def is_spam(self, event):
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
            return True

        last_user_assign[event.author.id] = now
        return False

    async def handle_emoji(self, event):
        print("handle 1")
        if event.msg.id != self.msg.id:
            return

        old_page = self.shown_page
        # Check if it's a page reaction
        if event.reaction.emoji.name in [LARROW, RARROW]:
            # If yes, increment decrement things
            if event.reaction.emoji.name == LARROW:
                self.shown_page -= 1
            elif event.reaction.emoji.name == RARROW:
                self.shown_page += 1

        print("handle 2")
        # Check bounds
        if self.shown_page >= len(self.embeds):
            self.shown_page = 0
        elif self.shown_page < 0:
            self.shown_page = len(self.embeds) - 1

        # Send the new page
        if old_page != self.shown_page:
            await self.send_one_page(event)

        print("handle 3")
        # Build emoji lookup table
        self.build_emoji_lookup()

        print("handle 4")
        # Check if emoji exists
        if event.reaction.emoji.name not in self.crt_emoji_to_func:
            return

        # If it's an async function, await else just call
        target_func, label = self.crt_emoji_to_func[event.reaction.emoji.name]
        print("handle 5")
        try:
            if inspect.iscoroutinefunction(target_func):
                await target_func(event, label)
                print("handle 6.1")
            else:
                target_func(event, label)
                print("handle 6.2")
        except:
            import traceback

            traceback.print_exc()

    # handle_react is the event handler to be passed to hook2
    async def handle_react(self, event):
        # Handle the event
        print(f"Handling react by author {event.author.name}, emoji {event.reaction.emoji.name}, msg id {event.msg.id}")
        try:
            await self.handle_emoji(event)
        except:
            import traceback

            traceback.print_exc()

        # Remove the reaction
        await event.msg.async_remove_reaction(event.reaction.emoji.name, event.author)


class RoleSelector(Selector):
    # If N seconds have passed since the last role update, check the server status
    ROLE_UPDATE_INTERVAL = 60

    def __init__(self, server, channel, roles, title, max_selectable, hook):
        super().__init__(
            title=title,
            footer=f"Max selectable: {max_selectable if max_selectable > 0 else 'Unlimited' }",
            call_dict={},
            server=server,
            channel=channel,
            hook=hook,
        )

        self.roles = roles
        self.max_selectable = max_selectable
        self.last_role_update = 0

        self.update_role_list()

    def update_role_list(self):
        """
        Update roles in case a role name has changed
        """

        # Check if we need to get the roles
        if tutils.tnow() - self.last_role_update > RoleSelector.ROLE_UPDATE_INTERVAL:
            # Get the roles
            roles = dutils.get_roles_from_ids(self.roles, self.server)

            self.name_to_role = {}  # Map names to roles for quick lookup
            role_list = list()
            for role in roles:
                self.name_to_role[role] = roles[role]
                role_list.append(role)

            role_list = sorted(list(role_list), key=str.casefold)

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
        if await self.is_spam(event):
            return

        the_role = self.name_to_role[label]
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

    def serialize(self):
        data = super().serialize()
        data["max_selectable"] = self.max_selectable
        data["title"] = self.title

        return data

    @staticmethod
    async def deserialize(bot, data, hook, event):
        # Get the server and channel
        server, chan = RoleSelector.get_server_chan(bot, data)
        if not server or not chan:
            return

        # Create the selector
        selector = RoleSelector(
            server, chan, data["role_ids"], data["title"], data["max_selectable"], hook
        )

        await selector.finish_deserialize(bot, data, event)

        return selector


class RoleSelectorInterval(RoleSelector):
    def __init__(
        self, server, channel, first_role, last_role, title, max_selectable, hook
    ):
        super(RoleSelector, self).__init__(
            title=title,
            footer="Max selectable: %d" % max_selectable,
            call_dict={},
            server=server,
            channel=channel,
            hook=hook,
        )

        self.first_role = first_role
        self.last_role = last_role
        self.max_selectable = max_selectable
        self.last_role_update = 0

        self.update_role_list()

    def update_role_list(self):
        # Check if we need to get the roles
        if tutils.tnow() - self.last_role_update > RoleSelector.ROLE_UPDATE_INTERVAL:
            # Get the roles
            roles = dutils.get_roles_between(
                self.first_role, self.last_role, self.server
            )

            self.name_to_role = {}  # Map names to roles for quick lookup
            role_list = OrderedDict()  # Role list to pass to the selector
            for role in roles:
                self.name_to_role[role.name] = role
                role_list[role.name] = self.do_stuff

            role_list = OrderedDict(
                sorted(role_list.items(), key=lambda m: str.casefold(m[0]))
            )

            # Mark last role update time
            self.last_role_update = tutils.tnow()

            # Set the items
            self.set_items(role_list)

    async def handle_emoji(self, event):
        # Before handling an emoji, update the role list
        self.update_role_list()

        await super().handle_emoji(event)

    def serialize(self):
        data = super().serialize()
        data["first_role_id"] = dutils.get_role_by_name(self.server, self.first_role).id
        data["last_role_id"] = dutils.get_role_by_name(self.server, self.last_role).id
        data["max_selectable"] = self.max_selectable
        data["title"] = self.title

        return data

    @staticmethod
    async def deserialize(bot, data, hook, event):
        # Get the server and channel
        server, chan = RoleSelectorInterval.get_server_chan(bot, data)
        if not server or not chan:
            return

        # Get the roles
        first_role = dutils.get_role_by_id(server, data["first_role_id"])
        last_role = dutils.get_role_by_id(server, data["last_role_id"])

        if not first_role:
            print(
                "Could not find frole id %s/%s" % (data["server_id"], data["first_role_id"]),
            )
            return None

        if not last_role:
            print(
                "Could not find lrole id %s/%s" % (data["server_id"], data["last_role_id"]),
            )
            return None

        # Create the selector
        selector = RoleSelectorInterval(
            server,
            chan,
            first_role.name,
            last_role.name,
            data["title"],
            data["max_selectable"],
            hook,
        )

        await selector.finish_deserialize(bot, data, event)

        return selector
