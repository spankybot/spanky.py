import secrets
from collections import OrderedDict, deque
from itertools import chain

import plugins.paged_content as paged
import spanky.utils.discord_utils as dutils
from spanky.utils.carousel import Selector

from spanky.plugin import hook
from spanky.plugin.permissions import Permission
from spanky.plugin.event import EventType

from spanky.utils import time_utils as tutils

REQUIRED_ACCESS_ROLES = ["Valoare", "Gradi"]
NSFW_FORBID_ROLE = "Gradi"

CAT_TYPES = ["managed", "unmanaged", "archive"]
PRIVACY = ["public", "private", "invite"]
MSG_TIMEOUT = 2  # Timeout after which the message dissapears

# Roddit and test server
SRV = [
    "287285563118190592",
    "297483005763780613"]

JOIN_EMOTE = "✅"
advert_queue = deque(maxlen=50)


class AdvertObj():
    def __init__(self, server, storage, chname, msg):
        self.server = server
        self.storage = storage
        self.chname = chname
        self.msg = msg


@hook.command(server_id=SRV)
async def advertise(text, async_send_message, server, storage, event):
    """
    <channel [description]> - advertise a channel by optionally specifying a channel description
    """
    # Check minimum requirements
    text = text.split(maxsplit=1)
    if len(text) == 0:
        await async_send_message("Needs a channel name and optionally a description")

    # Get the target channel
    target_chan, _ = get_irc_chan(server, storage, dutils.str_to_id(text[0]))
    if not target_chan:
        await async_send_message("%s is not a channel" % text)
        return

    descr = ""
    if len(text) == 2:
        descr = text[1]

    # Send the message
    em = dutils.prepare_embed("Join %s" % target_chan.name, descr,
                              footer_txt="Click on %s react to join" % JOIN_EMOTE)
    msg = await async_send_message(embed=em)

    # Add react
    await msg.async_add_reaction(JOIN_EMOTE)

    # Add to queue
    advert_queue.append(AdvertObj(server, storage, text[0], msg))


@hook.event(EventType.reaction_add)
async def parse_react(bot, event):
    # Find the target object
    if event.reaction.emoji.name != JOIN_EMOTE:
        return

    found = None
    for obj in advert_queue:
        if obj.msg.id == event.msg.id:
            print(obj.msg.id)
            found = obj
            break

    if found == None:
        return

    await found.msg.async_remove_reaction(JOIN_EMOTE, event.author)
    await toggle_chan_presence(found.server, found.storage, found.chname, event, ToggleType.JOIN)


class ToggleType():
    JOIN = 1
    PART = 2
    NONE = 99


class BotCateg():
    def __init__(self, data):
        self._data = data

    @property
    def is_private(self):
        return self._data["privacy"] == "private"

    @property
    def is_public(self):
        return self._data["privacy"] == "public"

    @property
    def is_invite(self):
        return self._data["privacy"] == "invite"

    @property
    def is_archive(self):
        return self.chtype == "archive"

    @property
    def is_managed(self):
        return self.chtype == "managed"

    @property
    def is_unmanaged(self):
        return self.chtype == "unmanaged"

    @property
    def id(self):
        return self._data["id"]

    @property
    def name(self):
        return self._data["name"]

    @property
    def privacy(self):
        return self._data["privacy"]

    @property
    def chtype(self):
        return self._data["type"]


def get_bot_categs(server, storage):
    if "bot_cats" not in storage:
        return []

    for cat in storage["bot_cats"]:
        if server:
            # Check for changed names
            raw_cat = server.find_category_by_id(cat["id"])
            if cat["name"] != raw_cat.name:
                cat["name"] = raw_cat.name
                storage.sync()

        yield BotCateg(cat)


class ChanSelector(Selector):
    TOTAL_LEN = 80
    UPDATE_INTERVAL = 180

    def __init__(self, server, channel, storage):
        super().__init__(
            title="r/Romania channels",
            footer="Select to join/part channel.",
            call_dict={},
            max_rows=16)

        self.server = server
        self.channel = channel
        self.storage = storage
        self.last_role_update = 0

        self.update_role_list()

    def update_role_list(self):
        # Check if we need to get the roles
        if tutils.tnow() - self.last_role_update > ChanSelector.UPDATE_INTERVAL:
            roles = []
            # Get all channels
            for cat in get_bot_categs(self.server, self.storage):
                # skip the archive
                if cat.is_archive or cat.is_invite:
                    continue

                for chan in self.server.get_chans_in_cat(cat.id):
                    # Build a line
                    crt_name = f"**{chan.name}**"
                    if chan.topic:
                        crt_name += " " + chan.topic

                    # Clip line length
                    if len(crt_name) > ChanSelector.TOTAL_LEN:
                        crt_name = crt_name[:ChanSelector.TOTAL_LEN] + "..."
                    roles.append(crt_name)

            role_dict = OrderedDict()
            for role in sorted(roles):
                role_dict[role] = self.do_stuff

            # Mark last role update time
            self.last_role_update = tutils.tnow()

            # Set the items
            self.set_items(role_dict)

    def serialize(self):
        data = {}
        data["server_id"] = self.server.id
        data["channel_id"] = self.channel.id
        data["msg_id"] = self.get_msg_id()
        data["shown_page"] = self.shown_page

        return data

    @staticmethod
    async def deserialize(bot, data):
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

        # Create the selector
        selector = ChanSelector(
            server,
            chan,
            bot.server_permissions[server.id].get_plugin_storage(
                "plugins_custom_roddit_irc_mode.json"))

        # Set selector page
        selector.shown_page = data["shown_page"]

        # Rebuild message cache
        msg_id = data["msg_id"]

        # Get the saved message and set it
        msg = await chan.async_get_message(msg_id)
        selector.msg = msg

        # Add message to backend cache
        bot.backend.add_msg_to_cache(msg)

        # Remove reacts from other people
        await selector.reset_reacts(bot)

        return selector

    async def handle_emoji(self, event):
        # Before handling an emoji, update the role list
        self.update_role_list()

        await super().handle_emoji(event)

    async def do_stuff(self, event, label):
        # Check for role assign spam
        if await self.is_spam(event):
            return

        # Get the channel name
        chname = label.split("**")[1]
        await toggle_chan_presence(self.server, self.storage, chname, event, ToggleType.NONE)


async def toggle_chan_presence(server, storage, chname, event, force_toggle):
    # Lookup channel
    target_chan, categ = get_irc_chan(
        server, storage, dutils.str_to_id(chname))

    if not target_chan:
        await event.async_send_message(
            "<@%s>: Invalid channel name" % (event.author.id),
            timeout=MSG_TIMEOUT,
            check_old=False)
        return

    # Check if trying to join an invite-only channel
    if categ.is_invite and force_toggle == ToggleType.JOIN:
        return

    # Check for minimum requirements
    can_access = False
    for access_role in REQUIRED_ACCESS_ROLES:
        if dutils.user_has_role_name(event.author, access_role):
            can_access = True

    if not can_access:
        await event.async_send_message(
            "<@%s>: You can't join/leave a channel" % (event.author.id),
            timeout=MSG_TIMEOUT,
            check_old=False)
        return

    # Check if banned
    if is_banned(storage, target_chan, event.author):
        await event.async_send_message(
            "<@%s>: You are banned from %s." % (
                event.author.id, target_chan.name),
            timeout=MSG_TIMEOUT,
            check_old=False)
        return

    # Check if OP
    if is_channel_op(target_chan, event.author):
        await event.async_send_message(
            "<@%s>: OPs can't leave a channel that they operate." % (
                event.author.id),
            timeout=MSG_TIMEOUT,
            check_old=False)
        return

    # Check for NSFW chans
    if target_chan.is_nsfw:
        if dutils.user_has_role_name(event.author, NSFW_FORBID_ROLE):
            await event.async_send_message(
                "<@%s>: You cant join a NSFW channel" % (event.author.id),
                timeout=MSG_TIMEOUT,
                check_old=False)
            return

    if categ.is_private or categ.is_invite:
        # Get the role associated with the channel
        channel_role = give_assoc_role(server, storage, target_chan)

        # Check if we need to add or remove from channel
        needs_adding = True
        if is_permission_based(target_chan, storage):
            # Handle permission based access
            crt_users = list_members_perm_access(target_chan)
            for user in crt_users:
                if event.author.id == user.id:
                    needs_adding = False
        else:
            # Handle role based access
            if dutils.user_has_role_name(event.author, channel_role.name):
                needs_adding = False

        if force_toggle == ToggleType.JOIN:
            needs_adding = True
        elif force_toggle == ToggleType.PART:
            needs_adding = False

        # If the user wants to be removed
        if not needs_adding:
            if is_permission_based(target_chan, storage):
                await remove_from_overwrites(target_chan, event.author)
            else:
                event.author.remove_role(
                    dutils.get_role_by_name(server, channel_role.name))

            await event.async_send_message(
                "<@%s>: Removed you from `%s`" % (event.author.id, chname),
                timeout=MSG_TIMEOUT,
                check_old=False)
            return
        else:
            if is_permission_based(target_chan, storage):
                await set_channel_member(target_chan, event.author)
            else:
                # Add the role
                event.author.add_role(
                    dutils.get_role_by_name(server, channel_role.name))

            await event.async_send_message(
                "<@%s>: Added you to `%s`" % (event.author.id, chname),
                timeout=MSG_TIMEOUT,
                check_old=False)

    elif categ.is_public:
        # Check if the user wants to leave
        in_channel = True
        for user in get_removed_users(target_chan):
            if user.id == event.author.id:
                in_channel = False

        if force_toggle == ToggleType.JOIN:
            in_channel = False
        elif force_toggle == ToggleType.PART:
            in_channel = True

        if in_channel:
            await ignore_channel(target_chan, event.author)
            await event.async_send_message(
                "<@%s>: Removed you from `%s`" % (event.author.id, chname),
                timeout=MSG_TIMEOUT,
                check_old=False)
            return

        else:
            await remove_from_overwrites(target_chan, event.author)
            await event.async_send_message(
                "<@%s>: Added you to `%s`" % (event.author.id, chname),
                timeout=MSG_TIMEOUT,
                check_old=False)


@hook.command(server_id=SRV)
async def join(server, storage, event, text):
    """
    <chname> - join a channel
    """
    await toggle_chan_presence(server, storage, text, event, ToggleType.JOIN)


@hook.command(server_id=SRV)
async def part(server, storage, event, text):
    """
    <chname> - leave a channel
    """
    chan_name = ""
    if text == "":
        chan_name = event.channel.name
    else:
        chan_name = text

    await toggle_chan_presence(server, storage, chan_name, event, ToggleType.PART)

    # Delete the message
    event.msg.delete_message()


@hook.command(server_id=SRV)
async def vreau_canal(event, storage):
    """
    Generate channel selector
    """
    sel = ChanSelector(
        server=event.server,
        channel=event.channel,
        storage=storage)

    await sel.do_send(event)


def get_bot_categ_by(server, storage, name_or_id):
    for cat in get_bot_categs(server, storage):
        if cat.name == name_or_id or cat.id == name_or_id:
            return cat


def get_removed_users(channel):
    """
    List of users ignoring a channel
    """
    users = []
    for user, perm in channel.get_user_overwrites():
        if perm._raw.read_messages == False:
            users.append(user)

    return users


def get_operator_users(channel):
    """
    List of users operating a channel
    """
    users = []
    for user, perm in channel.get_user_overwrites():
        if perm._raw.manage_messages == True:
            users.append(user)

    return users


async def set_channel_op(chan, user):
    await chan.set_user_overwrite(
        user,
        send_messages=True,
        read_messages=True,
        read_message_history=True,
        manage_messages=True,
        attach_files=True,
        embed_links=True,
        external_emojis=True,
        add_reactions=True,
        create_instant_invite=True,
        manage_channels=True,
        manage_webhooks=True)


async def set_channel_member(chan, user):
    await chan.set_user_overwrite(
        user,
        send_messages=True,
        read_messages=True,
        read_message_history=True,
        attach_files=True,
        embed_links=True,
        external_emojis=True,
        add_reactions=True)


async def remove_from_overwrites(chan, user):
    await chan.remove_user_overwrite(
        user)


async def ignore_channel(chan, user):
    await chan.set_user_overwrite(
        user,
        send_messages=False,
        read_messages=False,
        read_message_history=False)


def get_irc_chans(server, storage):
    """
    Gets all the 'irc' channels in the server

    return: chan, category
    """

    for categ in get_bot_categs(server, storage):
        for chan in server.get_chans_in_cat(categ.id):
            yield chan, categ


def is_irc_chan(server, storage, name_or_id):
    """
    Gets all the 'irc' channels in the server

    return: chan, category
    """

    for categ in get_bot_categs(server, storage):
        for chan in server.get_chans_in_cat(categ.id):
            if name_or_id == chan.name or name_or_id == chan.id:
                return True

    return False


def is_channel_op(channel, user):
    for op in get_operator_users(channel):
        if user.name == op.name:
            return True

    return False


def get_chan_cat(server, storage, chan_id):
    for chan, cat in get_irc_chans(server, storage):
        if chan.id == chan_id:
            return cat

    return None


def get_irc_chan(server, storage, chan_name_or_id):
    for cat in get_bot_categs(server, storage):
        for chan in server.get_chans_in_cat(cat.id):
            if chan.id == chan_name_or_id or chan.name == chan_name_or_id:
                return chan, cat

    return None, None


async def create_prv_chan_role(server, chan, role_name):
    role = dutils.get_role_by_name(server, role_name)
    if not role:
        role = await server.create_role(role_name)

    await chan._raw.set_permissions(
        role._raw,
        send_messages=True,
        read_messages=True,
        read_message_history=True,
        attach_files=True,
        embed_links=True,
        external_emojis=True,
        add_reactions=True)

    return role


def list_members_role_access(server, storage, channel):
    """
    Get users that access a role based chan
    """
    users = []

    role = give_assoc_role(server, storage, channel)
    for user in server.get_users():
        if dutils.user_has_role_name(user, role.name):
            users.append(user)

    return users


def list_members_perm_access(channel):
    """
    Get users that access a permission based chan
    """
    users = []

    for user, perm in channel.get_user_overwrites():
        if perm._raw.send_messages == True:
            users.append(user)

    return users


def list_members_not_ignoring(channel):
    """
    Get users that do not ignore a channel
    """
    return channel.members_accessing_chan()


@hook.command(server_id=SRV, permissions=Permission.admin)
async def add_chan_category(server, text, reply, storage):
    """
    <category name or ID, type, privacy> - Add an existing channel category to the bot
    Types:
    - 'managed' category will have the permissions managed automatically by inheriting them from the parent category.
    - 'unmanaged' category will NOT have the permissions managed automatically.
    - 'archive' holds archived channels

    Privacy (only needed for managed and unmanaged types):
    - 'public' channels are joined/parted through the channel access list
    - 'private' channels are joined/parted through a channel specific role
    - 'invite' channels are joined through invite codes
    """
    text = text.split(" ")

    cat_name = text[0]
    cat_type = text[1]
    if cat_type not in CAT_TYPES:
        reply("Please specify a category: %s" % ", ".join(CAT_TYPES))
        return

    cat_privacy = None
    # Privacy needed for non-archive types
    if cat_type == "archive":
        cat_privacy = ""
    elif len(text) != 3:
        reply("Please specify name/ID, type, privacy")
    else:
        cat_privacy = text[2]

    name_or_id = dutils.str_to_id(cat_name).lower()
    cat_type = text[1]

    # Check for duplicates
    for cat in get_bot_categs(server, storage):
        if cat.name == name_or_id or cat.id == name_or_id:
            if cat["type"] != cat_type:
                cat["type"] = cat_type
                storage.sync()
                reply("Category updated to %s" % cat_type)
                return

    reply("Checking if %s exists" % name_or_id)
    for cat in server.get_categories():
        if cat.name.lower() == name_or_id or cat.id == name_or_id:
            if "bot_cats" not in storage:
                storage["bot_cats"] = []

            storage["bot_cats"].append(
                {
                    "name": cat.name,
                    "id": cat.id,
                    "type": text[1],
                    "privacy": cat_privacy
                }
            )

            storage.sync()
            reply("Found! Done!")
            return

    reply("Category not found")


@hook.command(server_id=SRV, permissions=Permission.admin, format="name")
async def del_chan_category(server, text, reply, storage):
    """
    <category name or ID> - Delete an existing channel category
    """
    name_or_id = dutils.str_to_id(text).lower()

    # Check for duplicates
    for cat in storage["bot_cats"]:
        if cat["name"].lower() == name_or_id or cat["id"] == name_or_id:
            storage["bot_cats"].remove(cat)
            storage.sync()
            reply("Done.")
            return

    reply("Category not found")


@hook.command(server_id=SRV, permissions=Permission.admin)
def list_chan_categories(server, storage):
    """
    List channel categories
    """
    cats = get_bot_categs(server, storage)

    msg = ""
    for cat in cats:
        if not cat.is_archive:
            msg += "Name: %s | ID: %s | Type: %s | Privacy: %s\n" % (
                cat.name, cat.id, cat.chtype, cat.privacy)
        else:
            msg += "Name: %s | ID: %s | Type: %s\n" % (
                cat.name, cat.id, cat.chtype)

    return dutils.code_block(msg)


async def bring_back_actives(server, storage, channel):
    users = {}
    async for msg in channel._raw.history(limit=None):
        users[msg.author.id] = msg.author

    for ignoring in get_removed_users(channel):
        if ignoring.id in users.keys():
            del users[ignoring.id]

    role = give_assoc_role(server, storage, channel)

    for raw_user in users.values():
        user = dutils.get_user_by_id(server, str(raw_user.id))
        print(raw_user.name)
        if not user:
            print("NOpe")
            continue

        user.add_role(role)


async def make_chan_private(server, storage, chan, cat):
    # Move it
    if cat.is_unmanaged:
        await chan.move_to_category(cat.id, sync_permissions=False)
    else:
        await chan.move_to_category(cat.id)

    # Restore OPs
    for op_id in storage["irc_chans"][chan.id]["ops"]:
        op = dutils.get_user_by_id(server, op_id)

        if not op:
            continue

        await set_channel_op(chan, op)

    if not is_permission_based(chan, storage):
        role = give_assoc_role(server, storage, chan)
        if not role:
            role = await create_prv_chan_role(server, chan, "%s-member" % chan.name)

        storage["irc_chans"][chan.id]["associated_roleid"] = role.id

    await save_server_cfg(server, storage)
    await bring_back_actives(server, storage, chan)


async def make_chan_public(server, storage, chan, cat):
    # Move it
    if cat.is_unmanaged:
        await chan.move_to_category(cat.id, sync_permissions=False)
    else:
        await chan.move_to_category(cat.id)

    # Restore OPs
    for op_id in storage["irc_chans"][chan.id]["ops"]:
        op = dutils.get_user_by_id(server, op_id)
        if not op:
            continue
        await set_channel_op(chan, op)

    # Restore ignores
    for ignoring_id in storage["irc_chans"][chan.id]["ignoring"]:
        ignoring = dutils.get_user_by_id(server, ignoring_id)

        if not ignoring:
            continue

        await ignore_channel(chan, ignoring)


async def make_chan_archived(server, storage, chan, cat):
    # Move it
    await chan.move_to_category(cat.id)


@hook.command(server_id=SRV, permissions=Permission.admin)
async def move_to_category(server, storage, text, event, reply):
    """
    Move a channel to a category
    """
    target_cat = get_bot_categ_by(server, storage, text)
    #crt_cat = get_chan_cat(server, storage, event.channel.id)

    transition_done = False
    if target_cat.is_private:
        await make_chan_private(server, storage, event.channel, target_cat)
        transition_done = True

    elif target_cat.is_public:
        await make_chan_public(server, storage, event.channel, target_cat)
        transition_done = True

    elif target_cat.is_archive:
        await make_chan_archived(server, storage, event.channel, target_cat)
        transition_done = True

    if not transition_done:
        reply("Invalid transition")
    else:
        reply("Done")
        await save_server_cfg(server, storage)


@hook.command(server_id=SRV, permissions=Permission.admin)
async def save_server_cfg(server, storage):
    if "irc_chans" not in storage:
        storage["irc_chans"] = {}

    for chan, cat in get_irc_chans(server, storage):
        elem = None
        if chan.id in storage["irc_chans"]:
            elem = storage["irc_chans"][chan.id]
        else:
            elem = {}
            elem["id"] = chan.id
            elem["name"] = chan.name
            elem["cat_id"] = cat.id
            elem["ops"] = []
            elem["bans"] = []
            elem["ignoring"] = []
            elem["permission_based"] = False
            elem["associated_roleid"] = ""

            assoc_role = dutils.get_role_by_name(
                server, "%s-member" % chan.name)
            if assoc_role:
                elem["associated_roleid"] = assoc_role.id

        for op in get_operator_users(chan):
            if op.id not in elem["ops"]:
                elem["ops"].append(op.id)

        for ignoring in get_removed_users(chan):
            if ignoring.id not in elem["ignoring"]:
                elem["ignoring"].append(ignoring.id)

        elem["ops"] = list(set(elem["ops"]))
        elem["ignoring"] = list(set(elem["ignoring"]))

        storage["irc_chans"][chan.id] = elem

    storage.sync()


def set_permission_based(chan, storage, ptype):
    storage["irc_chans"][chan.id]["permission_based"] = ptype
    storage.sync()


def is_permission_based(chan, storage):
    return storage["irc_chans"][chan.id]["permission_based"]


@hook.command(server_id=SRV, permissions=Permission.admin)
async def make_permission_based(server, storage, text, event, reply):
    """
    Instead of managing access through roles, it uses channel permissions
    """
    if not is_permission_based(event.channel, storage):
        set_permission_based(event.channel, storage, True)

    # Get current users accessing it
    crt_users = list_members_role_access(server, storage, event.channel)

    # Get the role
    chan_role = give_assoc_role(server, storage, event.channel)

    if not chan_role:
        reply("Could not get channel role")
        return

    for user in crt_users:
        print(user.name)
        await set_channel_member(event.channel, user)
        user.remove_role(chan_role)

    await server.delete_role_by_name(chan_role.name)
    reply("Done")


@hook.command(server_id=SRV, permissions=Permission.admin)
async def make_role_based(server, storage, text, event, reply):
    """
    Instead of managing access through permissions, it uses role access
    """
    if is_permission_based(event.channel, storage):
        set_permission_based(event.channel, storage, False)

    # Get current users accessing it
    crt_users = list_members_perm_access(event.channel)

    # Get the role
    chan_role = give_assoc_role(server, storage, event.channel)

    # Create it if it doesn't exist
    if not chan_role:
        chan_role = await create_prv_chan_role(server, event.channel, "%s-member" % chname)

    for user in crt_users:
        print(user.name)
        await remove_from_overwrites(event.channel, user)
        user.add_role(chan_role)

    reply("Done")


def get_users_in_chan(channel, server, storage):
    # Get the category
    crt_cat = get_chan_cat(server, storage, channel.id)

    users = []
    # List private members
    if crt_cat.is_private:
        if not is_permission_based(channel, storage):
            users = list_members_role_access(server, storage, channel)
        else:
            users = list_members_perm_access(channel)
    # List invite_only members
    elif crt_cat.is_invite:
        users = list_members_perm_access(channel)
    elif crt_cat.is_public:
        users = list_members_not_ignoring(channel)

    return users, crt_cat


@hook.command(server_id=SRV)
def list_members(server, storage, event):
    """
    List members
    """
    if not is_irc_chan(server, storage, event.channel.name):
        return "This channel is not managed by ops"

    users, cat = get_users_in_chan(event.channel, server, storage)
    if cat.is_public:
        return "Channel is public"
    else:
        return ", ".join(user.name for user in users)


@hook.command(server_id=SRV)
def list_ops(server, storage, event):
    """
    List operators
    """
    if not is_irc_chan(server, storage, event.channel.name):
        return "This channel is not managed by ops"

    ops = get_operator_users(event.channel)

    if len(ops) == 0:
        return "No channel ops set"

    return ", ".join(i.name for i in ops)


@hook.command(server_id=SRV)
async def add_op(text, event, server, storage, reply):
    """
    <name> - Add an operator
    """
    if not is_irc_chan(server, storage, event.channel.name):
        reply("This channel is not managed by ops")
        return

    if not is_channel_op(event.channel, event.author):
        reply("You need to be an OP.")
        return

    user = dutils.get_user_by_id(server, dutils.str_to_id(text))
    if not user:
        user = dutils.get_user_by_name(server, text)

    if not user:
        reply("Invalid user")
        return

    # Check if user in channel
    user_in_chan = False
    users, _ = get_users_in_chan(event.channel, server, storage)
    for crt_user in users:
        if user.id == crt_user.id:
            user_in_chan = True

    if not user_in_chan:
        reply("User not in channel")
        return

    await set_channel_op(event.channel, user)
    await save_server_cfg(server, storage)
    reply("Done!")


@hook.command(server_id=SRV)
async def remove_op(text, event, server, storage, reply):
    """
    <name> - Remove an operator
    """
    if not is_irc_chan(server, storage, event.channel.name):
        reply("This channel is not managed by ops")
        return

    if not is_channel_op(event.channel, event.author):
        reply("You need to be an OP.")
        return

    user = dutils.get_user_by_id(server, dutils.str_to_id(text))
    if not user:
        user = dutils.get_user_by_name(server, text)

    if not user:
        reply("Invalid user")
        return

    if not is_channel_op(event.channel, user):
        reply("User is not an OP.")
        return

    await remove_from_overwrites(event.channel, user)
    await save_server_cfg(server, storage)
    reply("Done!")


@hook.command(server_id=SRV)
async def kick_member(text, event, server, storage, reply):
    """
    <name/ID> - kick a member
    """
    if not is_irc_chan(server, storage, event.channel.name):
        reply("This channel is not managed by ops")
        return

    if not is_channel_op(event.channel, event.author):
        reply("You need to be an OP.")
        return

    user = dutils.get_user_by_id(server, dutils.str_to_id(text))
    if not user:
        reply("Could not find user")
        return

    # Get the category
    crt_cat = get_chan_cat(server, storage, event.channel.id)

    # Remove private members
    if crt_cat.is_private or crt_cat.is_invite:
        if not is_permission_based(event.channel, storage):
            role = give_assoc_role(server, storage, event.channel)
            user.remove_role(role)
        else:
            await remove_from_overwrites(event.channel, user)
        reply("Done!")
    elif crt_cat.is_public:
        # Remove private members
        await ignore_channel(event.channel, user)
        reply("Done!")


def add_to_banlist(storage, chan, member):
    if member.id in storage["irc_chans"][chan.id]["bans"]:
        return "Already banned"

    storage["irc_chans"][chan.id]["bans"].append(member.id)
    storage.sync()
    return "Done"


def remove_from_banlist(storage, chan, member):
    if member.id in storage["irc_chans"][chan.id]["bans"]:
        storage["irc_chans"][chan.id]["bans"].remove(member.id)
        storage.sync()
        return "Done"
    else:
        return "Not in banlist"


def is_banned(storage, chan, member):
    if member.id in storage["irc_chans"][chan.id]["bans"]:
        return True
    return False


@hook.command(server_id=SRV)
def list_bans(server, storage, event):
    """
    List channel bans
    """
    if not is_irc_chan(server, storage, event.channel.name):
        return "This channel is not managed by ops"

    if not is_channel_op(event.channel, event.author):
        return "You need to be an OP."

    users = []

    for banned_id in storage["irc_chans"][event.channel.id]["bans"]:
        user = dutils.get_user_by_id(server, banned_id)
        if user:
            users.append(user.name)

    if len(users) == 0:
        return "Empty"

    return ", ".join(users)


@hook.command(server_id=SRV)
async def ban_member(text, event, server, storage, reply):
    """
    <name/ID> - ban a member
    """
    if not is_irc_chan(server, storage, event.channel.name):
        reply("This channel is not managed by ops")
        return

    if not is_channel_op(event.channel, event.author):
        reply("You need to be an OP.")
        return

    user = dutils.get_user_by_id(server, dutils.str_to_id(text))
    if not user:
        reply("Could not find user")
        return

    # Get the category
    crt_cat = get_chan_cat(server, storage, event.channel.id)

    # Remove private members
    if crt_cat.is_private or crt_cat.is_invite:
        if not is_permission_based(event.channel, storage):
            role = give_assoc_role(server, storage, event.channel)
            user.remove_role(role)
        else:
            await remove_from_overwrites(event.channel, user)
    elif crt_cat.is_public:
        # Remove private members
        await ignore_channel(event.channel, user)

    await save_server_cfg(server, storage)
    add_to_banlist(storage, event.channel, user)
    await save_server_cfg(server, storage)
    reply("Done")


@hook.command(server_id=SRV)
async def unban_member(text, event, server, storage, reply):
    """
    <name/ID> - unban a member
    """
    if not is_irc_chan(server, storage, event.channel.name):
        reply("This channel is not managed by ops")
        return

    if not is_channel_op(event.channel, event.author):
        reply("You need to be an OP.")
        return

    user = dutils.get_user_by_id(server, dutils.str_to_id(text))
    if not user:
        reply("Could not find user")
        return

    remove_from_banlist(storage, event.channel, user)
    reply("Done")


def give_assoc_role(server, storage, channel):
    assoc_id = storage["irc_chans"][channel.id]["associated_roleid"]
    if assoc_id == "":
        return None

    return dutils.get_role_by_id(server, assoc_id)


@hook.command(server_id=SRV)
def get_associated_role(event, server, storage):
    """
    Get the role name associated to the channel
    """
    if not is_irc_chan(server, storage, event.channel.name):
        return "This channel is not managed by ops"

    if not is_channel_op(event.channel, event.author):
        return "You need to be an OP."

    if is_permission_based(event.channel, storage):
        return "This channel is accessed through permissions. It does not have a specific role."

    role = give_assoc_role(server, storage, event.channel)
    if not role:
        return "Could not get role"

    return role.name


@hook.command(server_id=SRV)
async def set_associated_role_name(text, event, server, storage, reply):
    """
    Set the role name associated to the channel
    """
    if not is_irc_chan(server, storage, event.channel.name):
        reply("This channel is not managed by ops")
        return

    if not is_channel_op(event.channel, event.author):
        reply("You need to be an OP.")
        return

    if is_permission_based(event.channel, storage):
        reply("This channel is accessed through permissions. It does not have a specific role.")
        return

    assoc_id = storage["irc_chans"][event.channel.id]["associated_roleid"]
    if assoc_id == "":
        reply("Unexpected error")
        return

    role = dutils.get_role_by_id(server, assoc_id)
    role.set_name(text)
    reply("Done")


@hook.command(server_id=SRV)
def irc_help():
    funcs = [
        set_topic,
        request_channel,
        list_members,
        list_ops,
        add_op,
        remove_op,
        kick_member,
        ban_member,
        unban_member,
        list_bans,
        get_associated_role,
        set_associated_role_name,
        invite_member]

    ret = "```\n"
    for func in funcs:
        ret += "%s - %s\n" % (func.__name__, func.__doc__.strip())

    return ret + "```"

# @hook.command(permissions=Permission.admin, server_id=SRV)
# async def sort_roles(server):
#     """
#     Sort roles alphabetically
#     """

#     # Get all roles
#     rlist = {}
#     for chan in chain(
#             server.get_chans_in_cat(PUB_CAT),
#             server.get_chans_in_cat(PRV_CAT)):
#         rlist["%s-op" % chan.name] = \
#             dutils.get_role_by_name(server, "%s-op" % chan.name)

#         member_role = dutils.get_role_by_name(server, "%s-member" % chan.name)
#         if member_role:
#             rlist["%s-member" % chan.name] = member_role

#     # Sort them and position starting from the first alphanumeric role
#     print("Base position is %s" % str(sorted(rlist.keys())[0]))
#     crt_pos = rlist[sorted(rlist.keys())[0]].position
#     for rname in sorted(rlist.keys()):
#         print("Setting %s to %d" % (rname, crt_pos))

#         if crt_pos != rlist[rname].position:
#             await rlist[rname].set_position(crt_pos)

#         crt_pos -= 1


async def sort_chans(server, categ):
    """
    Sort channels alphabetically
    """
    min_pos = 99999
    chans = {}
    for chan in server.get_chans_in_cat(categ.id):
        chans[chan.name] = chan
        min_pos = min(min_pos, chan.position)

    for cname in sorted(chans.keys()):
        if min_pos != chans[cname].position:
            await chans[cname].set_position(min_pos)

        min_pos += 1


@hook.command(permissions=Permission.admin, server_id=SRV)
async def check_irc_stuff(server, storage, reply):
    reply("Sorting channels")
    for categ in get_bot_categs(server, storage):
        if not categ.is_managed:
            continue

        print(categ.name)

        await sort_chans(server, categ)

    reply("Done")


@hook.command(server_id=SRV)
def request_channel(text, event, send_message):
    """
    <name> - request a channel by specifying a name
    """

    if len(text.split(" ")) != 1:
        return "Channel name must not contain spaces"

    message = "<@%s> has requested a channel named %s" % (
        event.author.id, text)
    send_message(target="449899630176632842", text=message)


@hook.command(permissions=Permission.admin, server_id=SRV)
async def create_channel(text, server, reply, storage):
    """
    <name type founder> - create a channel by specifying a 'name', type and who is the channel founder
    """

    # Check input
    text = text.split(" ")
    if len(text) != 3:
        reply(create_channel.__doc__)
        return

    # Parse data
    chname = text[0].lower()
    chtype = text[1].lower()
    user = dutils.get_user_by_id(server, dutils.str_to_id(text[2]))

    if not user:
        reply("Could not find given user")
        return

    categs = list(get_bot_categs(server, storage))
    # Get which category we want to create it in
    target_cat = None
    for cat in categs:
        if chtype == cat.name:
            target_cat = cat

    if not target_cat:
        reply("Channel type must be one of: %s" %
              ", ".join([i.name for i in categs]))
        return

    # Check dupes
    for chan, _ in get_irc_chans(server, storage):
        if chan.name == chname:
            reply("A channel by that name already exists")
            return

    new_chan = None
    if target_cat.is_public:
        new_chan = await server.create_text_channel(chname, target_cat.id)
    elif target_cat.is_private:
        new_chan = await server.create_text_channel(chname, target_cat.id)
    elif target_cat.is_invite:
        new_chan = await server.create_text_channel(chname, target_cat.id)
    else:
        raise NotImplemented("Invalid channel type")

    # Add the OP
    await set_channel_op(new_chan, user)
    await save_server_cfg(server, storage)

    if target_cat.is_private or target_cat.is_invite:
        set_permission_based(new_chan, storage, True)

    reply("Okay")


@hook.command(permissions=Permission.admin, server_id=SRV)
async def delete_channel(text, server, reply):
    """
    <channel> - delete a channel
    """
    text = text.split(" ")
    if len(text) != 1:
        reply("Please input a valid channel name")
        return

    chname = text[0]
    # Check dups public
    for chan in chain(server.get_chans_in_cat(PUB_CAT), server.get_chans_in_cat(PRV_CAT)):
        if chan.name == chname:
            await server.delete_channel(chan)
            await server.delete_role_by_name("%s-op" % chname)
            await server.delete_role_by_name("%s-member" % chname)

            reply("Done!")
            return

    reply("No channel named %s" % chname)


@hook.command(server_id=SRV)
def set_topic(server, storage, reply, event, text):
    """
    <topic> - set channel topic
    """
    if not is_irc_chan(server, storage, event.channel.name):
        return "This channel is not managed by ops"

    if not is_channel_op(event.channel, event.author):
        return "You need to be an OP."

    if event.channel.is_nsfw and "NSFW" not in text:
        text += " [NSFW]"

    event.channel.set_topic(text)


@hook.command(permissions=Permission.admin, server_id=SRV)
async def make_nsfw(server, storage, reply, event, text, send_message):
    """
    <topic> - make channel NSFW (only channel OPs can do it)
    """

    if not is_irc_chan(server, storage, event.channel.name):
        return "This channel is not managed by ops"

    if not is_channel_op(event.channel, event.author):
        return "You need to be an OP."

    target_chan, categ = get_irc_chan(server, storage, event.channel.id)
    if not categ.is_private:
        return "Only private channels can be made NSFW"

    # Set NSFW
    target_chan.set_nsfw(True)

    # Add NSFW to topic
    if target_chan.topic and "NSFW" not in target_chan.topic:
        target_chan.set_topic(text + " [NSFW]")

    # Purge non-NSFW users
    member_role = give_assoc_role(server, storage, target_chan)
    for user in target_chan.members_accessing_chan():
        for urole in user.roles:
            if urole.name == NSFW_FORBID_ROLE:
                user.remove_role(member_role)
                await remove_from_overwrites(target_chan, user)
                send_message("Parted @%s - because channel was made NSFW" %
                             user.id, target=target_chan.id)

                user.send_pm("You have been removed from %s, because the channel was made NSFW." %
                             target_chan.name)


@hook.command(permissions=Permission.admin, server_id=SRV)
def make_sfw(server, storage, reply, event, text):
    """
    <topic> - make channel SFW (only channel OPs can do it)
    """

    if not is_irc_chan(server, storage, event.channel.name):
        return "This channel is not managed by ops"

    if not is_channel_op(event.channel, event.author):
        return "You need to be an OP."

    target_chan, _ = get_irc_chan(server, storage, event.channel.id)

    # Set NSFW
    target_chan.set_nsfw(False)


@hook.command(permissions=Permission.admin, server_id=SRV)
def get_orphan_chans(storage):
    """
    Get channels without ops
    """
    orphan = []

    for chan in storage["irc_chans"].values():
        if len(chan["ops"]) == 0:
            orphan.append(chan["name"])

    return ", ".join(orphan)


def cleanup_expired_invites(storage):
    # Bail if no invite ids list
    if not storage["invite_ids"]:
        return

    for invite in storage["invite_ids"]:
        # Older than a day?
        if tutils.tnow() - invite["create_time"] >= tutils.SEC_IN_DAY:
            storage["invite_ids"].remove(invite)

    storage.sync()


def cleanup_invite_by_id(storage, invite_id):
    # Bail if no invite ids list
    if not storage["invite_ids"]:
        return

    for invite in storage["invite_ids"]:
        # Older than a day?
        if invite["invite_id"] == invite_id:
            storage["invite_ids"].remove(invite)

    storage.sync()


@hook.command(server_id=SRV)
def invite_member(event, server, storage, text):
    """
    <user> Invite someone to an invite-only channel
    """

    if not is_channel_op(event.channel, event.author):
        return "You need to be an OP."

    # Check if command was issued in an invite-only channel
    in_invite_chan = False
    for chan, _ in get_irc_chans(server, storage):
        if chan.id == event.channel.id:
            in_invite_chan = True

    if not in_invite_chan:
        return "Invites can only be sent from invite-only channels"

    # Get targeted user
    user = dutils.get_user_by_id(server, dutils.str_to_id(text))
    if not user:
        return "Could not get user"

    # Check if banned
    if is_banned(storage, event.channel, user):
        return "User is banned from this channel"

    already_in_chan = False
    for crt_user, perm in event.channel.get_user_overwrites():
        if perm._raw.send_messages == True:
            if user.id == crt_user.id:
                already_in_chan = True

    if already_in_chan:
        return "User already in channel"

    # if "invite_ids" not in storage:
    storage["invite_ids"] = []

    # Clean up old invites
    cleanup_expired_invites(storage)

    # Generate a random invite ID string
    # Collisions highly improbable - TODO check?
    invite_id = secrets.token_urlsafe(8)

    new_invite = {}
    new_invite["user_id"] = user.id
    new_invite["channel_id"] = event.channel.id
    new_invite["invite_id"] = invite_id
    new_invite["create_time"] = tutils.tnow()

    storage["invite_ids"].append(new_invite)
    storage.sync()

    user.send_pm(
        f"You have been invited to {event.channel.name}.\nReply with the following command to accept the invite:")
    user.send_pm(f".accept_invite {invite_id}")
    return "Done!"


@hook.command(can_pm=True)
async def accept_invite(bot, text, event):
    # Go through server IDs
    for server in bot.backend.get_servers():
        if server.id not in SRV:
            continue

        # Get storage
        storage = bot.server_permissions[server.id].get_plugin_storage(
            "plugins_custom_roddit_irc_mode.json")

        # Bail if no invite ids list
        if not storage["invite_ids"]:
            continue

        # Clean up old invites
        cleanup_expired_invites(storage)

        # Check for a match
        for invite in storage["invite_ids"]:
            if invite["invite_id"] == text and invite["user_id"] == event.author.id:
                # Add member to channel
                chan = dutils.get_channel_by_id(server, invite["channel_id"])
                user = dutils.get_user_by_id(server, event.author.id)
                await set_channel_member(chan, user)

                # Cleanup used invite
                cleanup_invite_by_id(storage, invite["invite_id"])

                # Reply to the user
                event.author.send_pm("Done!")


# Experimental stuff

class ActionType():
    SET = 0
    GET = 1
    CLEAR = 2


def test123(storage, chan, value, action_type):
    """
    muie dinamo
    """
    pass


def irc_motd(storage, chan, value, action_type):
    """
    Manage channel MOTD
    """

    if action_type == ActionType.SET:
        storage["irc_chans"][chan.id]["motd"] = value

        return "MOTD set"

    elif action_type == ActionType.GET:
        if not "motd" in storage["irc_chans"][chan.id]:
            return "Not set"

        return storage["irc_chans"][chan.id]["motd"]

    elif action_type == ActionType.CLEAR:
        del storage["irc_chans"][chan.id]["motd"]
        return "MOTD cleared"


SETGET_CMDS = {
    "motd": irc_motd,
    "test1": test123
}


def launch_icmd(server, storage, channel, action_type, text):
    # Get channel
    target_chan, _ = get_irc_chan(server, storage, channel.id)

    # Split command
    text = text.split(" ", maxsplit=1)
    if text[0] in SETGET_CMDS.keys():
        func = SETGET_CMDS[text[0]]

        args = ""
        if len(text) > 1:
            args = text[1]

        ret_val = func(storage, target_chan, args, action_type)
        storage.sync()

        return ret_val


@hook.command(server_id=SRV)
async def iset(event, server, storage, text, reply):
    """
    Set a channel property. Available properties:\n{SUBCMDS}
    """

    if not is_channel_op(event.channel, event.author):
        reply("You need to be an OP.")
        return

    reply(launch_icmd(server, storage, event.channel, ActionType.SET, text))


@hook.command(server_id=SRV)
async def iget(event, server, storage, text, reply):
    """
    Get a channel property. Available properties:\n{SUBCMDS}
    """

    if not is_channel_op(event.channel, event.author):
        reply("You need to be an OP.")
        return

    reply(launch_icmd(server, storage, event.channel, ActionType.GET, text))


@hook.command(server_id=SRV)
async def iclear(event, server, storage, text, reply):
    """
    Clear a channel property. Available properties:\n{SUBCMDS}
    """

    if not is_channel_op(event.channel, event.author):
        reply("You need to be an OP.")
        return

    reply(launch_icmd(server, storage, event.channel, ActionType.CLEAR, text))


def gen_ihelp():
    reply = ""
    for func_name, func in SETGET_CMDS.items():
        reply += "-> %s - %s\n" % (func_name, func.__doc__.strip())

    return reply


iset.__doc__ = iset.__doc__.format(SUBCMDS=gen_ihelp())
iget.__doc__ = iset.__doc__.format(SUBCMDS=gen_ihelp())
iclear.__doc__ = iset.__doc__.format(SUBCMDS=gen_ihelp())


# @hook.command(permissions=Permission.admin, server_id=SRV)
# def list_invites(storage):
#     """
#     List pending invites
#     """
#     # Bail if no invite ids list
#     if not storage["invite_ids"]:
#         return "Empty"

#     reply = ""
#     for invite in storage["invite_ids"]:
#         reply += "" + invite["invite_id"] + "\n"

#     return reply
