from itertools import chain

import plugins.paged_content as paged
import spanky.utils.discord_utils as dutils
from spanky.utils.carousel import Selector

from spanky.plugin import hook
from spanky.plugin.permissions import Permission
from spanky.utils import time_utils as tutils
from collections import OrderedDict


PUB_CAT = "public"
PRV_CAT = "private"
INV_CAT = "invite"
CHTYPES = [PUB_CAT, PRV_CAT]

REQUIRED_ACCESS_ROLES = ["Valoare", "Gradi"]
NSFW_FORBID_ROLE = "Gradi"

CAT_TYPES = ["managed", "unmanaged", "archive", "public", "private"]
MSG_TIMEOUT = 3  # Timeout after which the message dissapears

# Roddit and test server
SRV = [
    "287285563118190592",
    "297483005763780613"]

def get_bot_categs(storage, server):
    if "bot_cats" not in storage:
        return []

    for cat in storage["bot_cats"]:
        if server:
            # Check for changed names
            raw_cat = server.find_category_by_id(cat["id"])
            if cat["name"] != raw_cat.name:
                cat["name"] = raw_cat.name
                storage.sync()

        yield cat

class ChanSelector(Selector):
    TOTAL_LEN = 80
    UPDATE_INTERVAL = 180

    def __init__(self, server, channel, storage):
        super().__init__(
            title="r/Romania channels",
            footer="Select to join/part channel.",
            call_dict={})

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
            for cat in get_bot_categs(self.storage, self.server):
                for chan in self.server.get_chans_in_cat(cat["id"]):
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
        await selector.remove_nonbot_reacts(bot)

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

        # Lookup channel
        target_chan, categ = find_irc_chan(
            self.server, self.storage, chan_name=chname)

        if not target_chan:
            return

        if categ["type"] == PRV_CAT:
            # Check if user is an OP
            if dutils.user_has_role_name(event.author, "%s-op" % chname):
                await event.async_send_message(
                    "<@%s>: OPs can't join/leave a channel that they operate." % (event.author.id),
                    timeout=MSG_TIMEOUT,
                    check_old=False)
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

            # Check for NSFW chans
            if target_chan.is_nsfw:
                if dutils.user_has_role_name(event.author, NSFW_FORBID_ROLE):
                    await event.async_send_message(
                        "<@%s>: You cant join a NSFW channel" % (event.author.id),
                        timeout=MSG_TIMEOUT,
                        check_old=False)
                    return

            # Check if user is a member
            if dutils.user_has_role_name(event.author, "%s-member" % chname):
                event.author.remove_role(
                        dutils.get_role_by_name(self.server, "%s-member" % chname))

                await event.async_send_message(
                    "<@%s>: Removed you from `%s`" % (event.author.id, chname),
                    timeout=MSG_TIMEOUT,
                    check_old=False)
                return

            # Add the role
            event.author.add_role(
                dutils.get_role_by_name(self.server, "%s-member" % target_chan.name))

            await event.async_send_message(
                "<@%s>: Added you to `%s`" % (event.author.id, chname),
                timeout=MSG_TIMEOUT,
                check_old=False)

        elif categ["type"] == PUB_CAT:
            # Check if the user wants to leave
            in_channel = True
            for user in target_chan.get_removed_users():
                if user.id == event.author.id:
                    in_channel = False

            if in_channel:
                target_chan.remove_user_by_permission(event.author)
                await event.async_send_message(
                    "<@%s>: Removed you from `%s`" % (event.author.id, chname),
                    timeout=MSG_TIMEOUT,
                    check_old=False)
                return

            else:
                target_chan.add_user_by_permission(event.author)
                await event.async_send_message(
                    "<@%s>: Added you to `%s`" % (event.author.id, chname),
                    timeout=MSG_TIMEOUT,
                    check_old=False)

@hook.command(server_id=SRV)
async def gibchan(event, storage):
    sel = ChanSelector(
        server=event.server,
        channel=event.channel,
        storage=storage)
    await sel.do_send(event)

def get_bot_categ_by(storage, name_or_id):
    for cat in storage["bot_cats"]:
        if cat["name"] == name_or_id or cat["id"] == name_or_id:
            return cat

@hook.command(server_id=SRV, permissions=Permission.admin, format="name type")
async def add_chan_category(server, text, reply, storage):
    """
    <category name or ID, type (managed, unmanaged)> - Add an existing channel category to the bot
    A 'managed' category will have the permissions managed automatically by inheriting them from the parent category.
    An 'unmanaged' category will NOT have the permissions managed automatically. Instead, there will still be channel OPs.
    """
    text = text.split(" ")

    if len(text) != 2:
        reply("Please specify name/ID manager/unmanaged")
        return

    if text[1] not in CAT_TYPES:
        reply("Please specify a category: %s" % ", ".join(CAT_TYPES))
        return

    name_or_id = dutils.str_to_id(text[0]).lower()
    cat_type = text[1]

    # Check for duplicates
    for cat in get_bot_categs(storage, server):
        if cat["name"] == name_or_id or cat["id"] == name_or_id:
            if cat["type"] != cat_type:
                cat["type"] = cat_type
                storage.sync()
                reply("Category updated to %s" % cat_type)
                return

    reply("Checking if %s exists" % name_or_id)
    for cat in server.get_categories():
        if cat.name == name_or_id or cat.id == name_or_id:

            if "bot_cats" not in storage:
                storage["bot_cats"] = []

            storage["bot_cats"].append(
                {
                    "name": cat.name,
                    "id": cat.id,
                    "type": text[1]
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
    for cat in get_bot_categs(storage, server):
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
    cats = get_bot_categs(storage, server)

    msg = ""
    for cat in cats:
        msg += "Name: %s | ID: %s | Type: %s\n" % (cat["name"], cat["id"], cat["type"])

    return dutils.code_block(msg)


@hook.command(server_id=SRV)
def irc_help():
    funcs = [
        list_chans,
        join,
        part,
        set_topic,
        request_channel]

    ret = "```\n"
    for func in funcs:
        ret += "%s - %s\n" % (func.__name__, func.__doc__.strip())

    return ret + "```"

@hook.command(permissions=Permission.admin, server_id=SRV)
async def sort_roles(server):
    """
    Sort roles alphabetically
    """

    # Get all roles
    rlist = {}
    for chan in chain(
            server.get_chans_in_cat(PUB_CAT),
            server.get_chans_in_cat(PRV_CAT)):
        rlist["%s-op" % chan.name] = \
            dutils.get_role_by_name(server, "%s-op" % chan.name)

        member_role = dutils.get_role_by_name(server, "%s-member" % chan.name)
        if member_role:
            rlist["%s-member" % chan.name] = member_role

    # Sort them and position starting from the first alphanumeric role
    print("Base position is %s" % str(sorted(rlist.keys())[0]))
    crt_pos = rlist[sorted(rlist.keys())[0]].position
    for rname in sorted(rlist.keys()):
        print("Setting %s to %d" % (rname, crt_pos))

        if crt_pos != rlist[rname].position:
            await rlist[rname].set_position(crt_pos)

        crt_pos -= 1

@hook.command(permissions=Permission.admin, server_id=SRV)
async def sort_chans(server, categ):
    """
    Sort channels alphabetically
    """
    min_pos = 99999
    chans = {}
    for chan in server.get_chans_in_cat(categ):
        chans[chan.name] = chan
        min_pos = min(min_pos, chan.position)

    for cname in sorted(chans.keys()):
        if min_pos != chans[cname].position:
            await chans[cname].set_position(min_pos)

        min_pos += 1


@hook.command(permissions=Permission.admin, server_id=SRV)
async def check_irc_stuff(server, reply):
    reply("Sorting channels")
    for chtype in CHTYPES:
        await sort_chans(server, chtype)

    reply("Creating roles")
    await resync_roles(server)
    reply("Sorting roles")
    await sort_roles(server)
    reply("Done")


@hook.command(permissions=Permission.admin, server_id=SRV)
async def resync_roles(server):
    """
    Go over all channels and set roles according to op/user access procedure
    """
    for chan in server.get_chans_in_cat(PUB_CAT):
        ignoring_this = list(chan.get_removed_users())
        await server.create_role(
            "%s-op" % chan.name,
            mentionable=True)
        await chan.move_to_category(PUB_CAT)
        await chan.set_op_role("%s-op" % chan.name)

        for user in ignoring_this:
            chan.remove_user_by_permission(user)

    for chan in server.get_chans_in_cat(PRV_CAT):
        ignoring_this = list(chan.get_removed_users())
        await server.create_role(
            "%s-op" % chan.name,
            mentionable=True)

        await server.create_role(
            "%s-member" % chan.name,
            mentionable=True)
        await chan.move_to_category(PRV_CAT)
        await chan.set_op_role("%s-op" % chan.name)
        await chan.set_standard_role("%s-member" % chan.name)

        for user in ignoring_this:
            chan.remove_user_by_permission(user)


@hook.command(server_id=SRV)
def request_channel(text, event, send_message):
    """
    <name type> - request a channel by specifying a 'name' and a type ('public', 'private' or 'invite')
    """

    text = text.split(" ")
    if len(text) != 2:
        return request_channel.__doc__

    # Parse data
    chname = text[0].lower()
    chtype = text[1].lower()

    if chtype not in CHTYPES:
        return "Channel type must be one of: %s" % str(CHTYPES)

    message = "<@%s> has requested a %s channel named %s" % (
        event.author.id, chtype, chname)
    send_message(target="449899630176632842", text=message)


@hook.command(permissions=Permission.admin, server_id=SRV)
async def create_channel(text, server, reply):
    """
    <name type founder> - create a channel by specifying a 'name', type (either 'public' or 'private') and who is the channel founder
    """
    # Check input
    text = text.split(" ")
    if len(text) != 3:
        return create_channel.__doc__

    # Parse data
    chname = text[0].lower()
    chtype = text[1].lower()
    user = dutils.get_user_by_id(server, dutils.str_to_id(text[2]))

    if not user:
        reply("Could not find given user")
        return

    if chtype not in CHTYPES:
        reply("Channel type must be one of: %s" % str(CHTYPES))
        return

    # Check dupes
    for chan in chain(server.get_chans_in_cat(PUB_CAT), server.get_chans_in_cat(PRV_CAT)):
        if chan.name == chname:
            reply("A channel by that name already exists")
            return

    await server.create_role(
        "%s-op" % chname,
        mentionable=True)

    if chtype == PUB_CAT:
        await server.create_text_channel(chname, PUB_CAT)
    elif chtype == PRV_CAT:
        await server.create_text_channel(chname, PRV_CAT)
        await server.create_role(
            "%s-member" % chname,
            mentionable=True)

    print("Created roles")
    await sort_roles(server)
    await sort_chans(server, PUB_CAT)
    await sort_chans(server, PRV_CAT)
    await resync_roles(server)

    # Add the OP
    user.add_role(
        dutils.get_role_by_name(server, "%s-op" % chname))
    print("Should be done!")


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


@hook.command(permissions=Permission.admin, server_id=SRV)
async def make_chan_private(text, server, reply):
    """
    <channel> - make a channel private
    """
    text = text.split(" ")
    if len(text) != 1:
        reply("Please input a valid channel name")
        return

    chdata = dutils.str_to_id(text[0])
    for chan in server.get_chans_in_cat(PUB_CAT):
        if chan.name == chdata or chan.id == chdata:
            await chan.move_to_category(PRV_CAT)
            await sort_chans(server, PRV_CAT)

            # Create the op role
            await server.create_role(
                "%s-op" % chan.name,
                mentionable=True)

            # Create the member role
            await server.create_role(
                "%s-member" % chan.name,
                mentionable=True)

            await resync_roles(server)

            reply("Done!")
            return

    reply("No public channel named %s" % chdata)


@hook.command(permissions=Permission.admin, server_id=SRV)
async def make_chan_public(text, server, reply):
    """
    <channel> - make a channel public
    """
    text = text.split(" ")
    if len(text) != 1:
        reply("Please input a valid channel name")
        return

    chdata = dutils.str_to_id(text[0])
    for chan in server.get_chans_in_cat(PRV_CAT):
        if chan.name == chdata or chan.id == chdata:
            await chan.move_to_category(PUB_CAT)
            await sort_chans(server, PUB_CAT)
            # Delete role
            await server.delete_role_by_name("%s-member" % chan.name)

            await resync_roles(server)

            reply("Done!")
            return

    reply("No private channel named %s" % chdata)

# @hook.command(server_id=SRV)
# def list_ops(server):

# @hook.command(server_id=SRV)
# def list_members(server):


def find_irc_chan(server, storage, chan_name=None, chan_id=None):
    if not chan_name and not chan_id:
        print("Needs one of name or id")
        return None

    for cat in get_bot_categs(storage, server):
        for chan in server.get_chans_in_cat(cat["id"]):
            if chan.id == chan_id or chan.name == chan_name:
                return chan, cat

    return None, None


def user_has_role(user, role_name):
    for urole in user.roles:
        if urole.name == role_name:
            return True

    return False


@hook.command(server_id=SRV)
def set_topic(server, storage, reply, event, text):
    """
    <topic> - set channel topic (only channel OPs can do it)
    """

    target_chan, _ = find_irc_chan(server, storage, chan_id=event.channel.id)
    if not target_chan:
        return "You're not in a user managed channel"

    # Check if user is OP
    has_right = user_has_role(
        event.author,
        "%s-op" % target_chan.name)

    if not has_right:
        return "Only channel OPs can do that"

    if target_chan.is_nsfw and "NSFW" not in text:
        text += " [NSFW]"

    target_chan.set_topic(text)


@hook.command(permissions=Permission.admin, server_id=SRV)
def make_nsfw(server, storage, reply, event, text, send_message):
    """
    <topic> - make channel NSFW (only channel OPs can do it)
    """

    target_chan, categ = find_irc_chan(server, storage, chan_id=event.channel.id)
    if not target_chan:
        return "You're not in a user managed channel"

    if categ["type"] == PUB_CAT:
        return "Only private channels can be made NSFW"

    # Check if user is OP
    has_right = user_has_role(
        event.author,
        "%s-op" % event.channel.name)

    if not has_right:
        return "Only channel OPs can do that"

    # Set NSFW
    target_chan.set_nsfw(True)

    # Add NSFW to topic
    if target_chan.topic and "NSFW" not in target_chan.topic:
        target_chan.set_topic(text + " [NSFW]")

    # Purge non-NSFW users
    member_role = dutils.get_role_by_name(server, "%s-member" % target_chan.name)
    op_role = dutils.get_role_by_name(server, "%s-op" % target_chan.name)
    for user in target_chan.members_accessing_chan():
        for urole in user.roles:
            if urole.name == NSFW_FORBID_ROLE:
                user.remove_role(member_role)
                user.remove_role(op_role)
                send_message("Part <@%s> - because channel was made NSFW" %
                             user.id, target=target_chan.id)

                user.send_pm("You have been removed from %s, because the channel was made NSFW." %
                             target_chan.name)


@hook.command(permissions=Permission.admin, server_id=SRV)
def make_sfw(server, storage, reply, event, text):
    """
    <topic> - make channel SFW (only channel OPs can do it)
    """

    target_chan, _ = find_irc_chan(server, storage, chan_id=event.channel.id)
    if not target_chan:
        return "You're not in a user managed channel"

    # Check if user is OP
    has_right = user_has_role(
        event.author,
        "%s-op" % event.channel.name)

    if not has_right:
        return "Only channel OPs can do that"

    # Set NSFW
    target_chan.set_nsfw(False)