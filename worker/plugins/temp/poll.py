import plugins.selector as selector
import utils.carousel as carousel
import utils.discord_utils as dutils
import plugins.paged_content as paged

from core.event import EventType
from core import hook
from hook.permissions import Permission

MSG_TIMEOUT = 3
active_polls = {}


class Poll(carousel.Selector):
    def __init__(self, server, channel, title, items, storage):
        self.server = server
        self.channel = channel

        self.items = items
        self.title = title
        self.is_active = True
        self.voted = []  # who voted
        self.score = {}  # score per item
        self.storage = storage
        for item in items:
            self.score[item] = 0

        item_dict = {}
        # Create callback for each item
        for item in items:
            # TODO quick clicking may end up in double vote?
            async def add_vote(event, label):
                # Check for role assign spam
                if await self.is_spam(event):
                    return

                # Check if author voted
                if event.author.id in self.voted:
                    await event.async_send_message(
                        "<@%s> You have already voted!" % event.author.id,
                        timeout=MSG_TIMEOUT,
                        check_old=False)
                    return
                else:
                    # Account voter
                    self.voted.append(event.author.id)

                # Increment voter count
                self.score[label] += 1

                await event.async_send_message(
                    "Thank you for voting!",
                    timeout=MSG_TIMEOUT,
                    check_old=False)
                sync_polls(self.storage)

            item_dict[item] = add_vote

        super(Poll, self).__init__(title=title, footer="", call_dict=item_dict)

        if server.id not in active_polls:
            active_polls[server.id] = []

        active_polls[server.id].append(self)

    def get_link(self):
        return dutils.return_message_link(
            self.server.id,
            self.channel.id,
            self.get_msg_id())

    async def get_results(self, async_send_message):
        results = []

        for key, val in self.score.items():
            results.append("%s: %s" % (key, val))

        content = paged.element(
            text_list=results,
            send_func=async_send_message,
            description="Poll results for %s" % self.title,
            max_lines=20,
            no_timeout=True)

        await content.get_crt_page()

    def serialize(self):
        # Create poll element
        elem = {}
        elem["title"] = self.title
        elem["items"] = self.items
        elem["server_id"] = self.server.id
        elem["channel_id"] = self.channel.id
        elem["msg_id"] = self.get_msg_id()
        elem["is_active"] = self.is_active
        elem["voted"] = self.voted
        elem["score"] = self.score
        elem["shown_page"] = self.shown_page

        return elem

    @staticmethod
    async def deserialize(bot, data, storage):
        # Don't rebuild inactive polls
        if not data["is_active"]:
            return None

        # Get the server
        server = None
        for elem in bot.get_servers():
            if elem.id == data["server_id"]:
                server = elem
                break

        if not server:
            print("Could not find server id %s" % data["server_id"])
            return None

        # Get the channel
        chan = dutils.get_channel_by_id(server, data["channel_id"])

        # Create the object
        poll = Poll(
            server,
            chan,
            data["title"],
            data["items"],
            storage)

        # Rebuild message cache
        msg_id = data["msg_id"]

        # Get the saved message and set it
        msg = await chan.async_get_message(msg_id)
        poll.msg = msg

        # Add message to backend cache
        bot.backend.add_msg_to_cache(msg)

        # Remove reacts from other people
        await poll.reset_reacts(bot)

        # Set other fields
        poll.is_active = data["is_active"]
        poll.voted = data["voted"]
        poll.score = data["score"]
        poll.shown_page = data["shown_page"]

        return poll


@hook.event(EventType.reaction_add)
async def parse_react(bot, event):
    if event.server.id not in active_polls:
        return

    # Check if the reaction was made on a message that contains a selector
    found_poll = None

    for poll in active_polls[event.server.id]:
        if poll.has_msg_id(event.msg.id):
            found_poll = poll
            break

    if not found_poll:
        return

    # Handle the event
    await found_poll.handle_emoji(event)

    # Remove the reaction
    await event.msg.async_remove_reaction(event.reaction.emoji.name, event.author)


def sync_polls(storage):
    if "polls" not in storage:
        storage["polls"] = {}

    for poll_list in active_polls.values():
        for poll in poll_list:
            elem = poll.serialize()
            storage["polls"][poll.get_link()] = elem
            storage.sync()


@hook.command(permissions=Permission.admin)
async def create_poll(text, event, storage, async_send_message):
    """
    <title %% option1 %% option2 %% ...> - create a poll with a title and multiple options
    """
    options = text.split(r"%%")

    # Remove whitespace
    for idx in range(len(options)):
        options[idx] = options[idx].strip()

    if len(options) < 3:
        await async_send_message("Needs at least a title and minimum two options.")
        return

    # Create the poll
    poll = Poll(event.server, event.channel, options[0], options[1:], storage)

    # Send it
    await poll.do_send(event, cache_it=False)

    # Sync all polls
    sync_polls(storage)


@hook.command(permissions=Permission.admin)
async def list_polls(async_send_message, storage, server):
    """
    Lists active polls
    """
    fields = {}

    if server.id not in active_polls:
        active_polls[server.id] = []

    for poll in active_polls[server.id]:
        if not poll.is_active:
            continue

        fields[poll.title] = poll.get_link()

    if len(fields.keys()) == 0:
        fields["No active polls"] = "Create a poll using `.create_poll`"

    embed = dutils.prepare_embed(
        title="Active polls",
        description="",
        fields=fields,
        inline_fields=None)

    await async_send_message(embed=embed)


@hook.command(permissions=Permission.admin)
async def close_poll(text, storage, async_send_message, server):
    """
    <message link> - Closes poll give in message link
    """
    if server.id not in active_polls:
        await async_send_message("No polls active")
        return

    for poll in active_polls[server.id]:
        if not poll.is_active:
            continue

        if text == poll.get_link():
            poll.is_active = False
            sync_polls(storage)
            await poll.get_results(async_send_message)
            return

    await async_send_message("Could not find the given poll")


@hook.on_ready()
async def rebuild_selectors(bot, server, storage):
    if "polls" not in storage:
        return

    for poll in storage["polls"].values():
        await Poll.deserialize(bot, poll, storage)
