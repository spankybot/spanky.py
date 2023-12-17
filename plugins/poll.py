import plugins.selector as selector
import spanky.utils.carousel as carousel
import spanky.utils.discord_utils as dutils
import plugins.paged_content as paged

from spanky.hook2 import EventType, ComplexCommand
from spanky.hook2 import Hook
from spanky.plugin.permissions import Permission

import nextcord.errors as nextcord_err

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from spanky.bot import Bot

hook = Hook("plugin_poll")

MSG_TIMEOUT = 3
active_polls: dict[str, list["Poll"]] = {}


class Poll(carousel.Selector):
    class InvalidMessage(Exception):
        pass

    def __init__(self, server, channel, title, items, storage, hook: Hook):
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

                if not self.is_active:
                    await event.async_send_message("Unfortunately, poll has closed!", timeout=MSG_TIMEOUT, check_old=False)
                    return

                # Check if author voted
                if event.author.id in self.voted:
                    await event.async_send_message(
                        "<@%s> You have already voted!" % event.author.id,
                        timeout=MSG_TIMEOUT,
                        check_old=False,
                    )
                    return
                else:
                    # Account voter
                    self.voted.append(event.author.id)

                # Increment voter count
                self.score[label] += 1

                await event.async_send_message(
                    "Thank you for voting!", timeout=MSG_TIMEOUT, check_old=False
                )
                sync_polls(self.storage, self.server)

            item_dict[item] = add_vote

        super(Poll, self).__init__(
            title=title,
            footer="",
            call_dict=item_dict,
            server=server,
            channel=channel,
            hook=hook,
            selector_type=carousel.SelectorType.PERMANENT,
        )

        if server.id not in active_polls:
            active_polls[server.id] = []

        active_polls[server.id].append(self)

    def get_link(self):
        return dutils.return_message_link(
            self.server.id, self.channel.id, self.get_msg_id()
        )

    async def get_results(self, async_send_message):
        results = []

        for key, val in self.score.items():
            results.append("%s: %s" % (key, val))

        content = paged.element(
            text_list=results,
            send_func=async_send_message,
            description="Poll results for %s" % self.title,
            max_lines=20,
            no_timeout=True,
        )

        await content.get_crt_page()

    def serialize(self):
        # Create poll element
        elem = super().serialize()
        elem["title"] = self.title
        elem["items"] = self.items
        elem["is_active"] = self.is_active
        elem["voted"] = self.voted
        elem["score"] = self.score

        return elem

    @staticmethod
    async def deserialize(bot: "Bot", data, hook: Hook, event):
        # Don't rebuild inactive polls
        if not data["is_active"]:
            print("Poll inactive")
            return None

        server, chan = Poll.get_server_chan(bot, data)
        if not server:
            return None
        if not chan:
            raise Poll.InvalidMessage("Invalid channel.")

        storage = hook.server_storage(server.id)

        # Rebuild message cache
        msg_id = data["msg_id"]

        if not msg_id:
            print(data)
            raise Poll.InvalidMessage("Invalid message ID.")

        # Create the object
        poll = Poll(server, chan, data["title"], data["items"], storage, hook)

        poll.is_active = data["is_active"]
        poll.voted = data["voted"]
        poll.score = data["score"]

        await poll.finish_deserialize(bot, data, event)

        return poll


def sync_polls(storage, server):
    if "polls" not in storage:
        storage["polls"] = {}

    for poll_list in active_polls.values():
        for poll in poll_list:
            # Don't add other polls to this server storage
            if poll.server.id != server.id:
                continue

            elem = poll.serialize()
            storage["polls"][poll.get_link()] = elem
            storage.sync()

poll_cmd = ComplexCommand(hook, "poll", permissions="admin", slash_servers=["287285563118190592"])


@poll_cmd.subcommand(name="create")
async def poll_create(text, event, storage, async_send_message, server):
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
    poll = Poll(event.server, event.channel, options[0], options[1:], storage, hook)

    # Send it
    await poll.do_send(event)  # , cache_it=False)

    # Sync all polls
    sync_polls(storage, server)

@poll_cmd.subcommand(name="list")
async def poll_list(async_send_message, storage, server):
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
        title="Active polls", description="", fields=fields, inline_fields=None
    )

    await async_send_message(embed=embed)


@poll_cmd.subcommand(name="close")
async def poll_close(text, storage, async_send_message, server):
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
            sync_polls(storage, server)
            await poll.get_results(async_send_message)
            return

    await async_send_message("Could not find the given poll")

@hook.command()
def create_poll():
    return "It's `.poll create` now."

@hook.command()
def list_polls():
    return "It's `.poll list` now."

@hook.command()
def close_poll():
    return "It's `.poll close` now.`"


async def rebuild_poll(bot, key, poll, storage, hook, event):
    try:
        return await Poll.deserialize(bot, poll, hook, event)
    except Poll.InvalidMessage:
        del storage["polls"][key]
        storage.sync()
    except nextcord_err.NotFound:
        poll["is_active"] = False
        storage.sync()
    except Exception as e:
        import traceback

        traceback.print_exc()


import asyncio


@hook.event(EventType.on_conn_ready)
async def rebuild_poll_selectors(bot, storage_getter, event):
    tasks = []
    for server in bot.backend.get_servers():
        storage = storage_getter(server.id)
        if "polls" not in storage:
            continue

        for key, poll in list(storage["polls"].items()):
            tasks.append(asyncio.create_task(rebuild_poll(bot, key, poll, storage, hook, event)))
    await asyncio.gather(*tasks)


@hook.command(permissions=["admin", "bot_owner"])
async def sanitize_polls(bot, storage_getter, server, storage, event):
    """
    TODO: clean up polls, fetch unregistered votes
    """

    # Fixes older bug where polls from other servers were being
    # added in one servers json
    for srv in bot.backend.get_servers():
        stor = storage_getter(srv.id)

        if "polls" not in stor:
            continue

        for key, val in list(stor["polls"].items()):
            if val["server_id"] != srv.id:
                del stor["polls"][key]
                stor.sync()

    # Rebuild polls
    if "polls" not in storage:
        return

    for key, val in storage["polls"].items():
        print("Rebuilding " + key)
        await rebuild_poll(bot, key, val, storage, hook, event)
