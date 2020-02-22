from itertools import chain

from spanky.plugin import hook
from spanky.plugin.permissions import Permission
from plugins.discord_utils import get_user_by_id, str_to_id, get_role_by_id, get_role_by_name

PUB_CAT = "public"
PRV_CAT = "private"
CHTYPES = [PUB_CAT, PRV_CAT]

REQUIRED_ACCESS_ROLES = ["Valoare"]
NSFW_FORBID_ROLE = "Gradi"

POS_START = "680559762760400987"
POS_END = "680559851474124802"
SRV = "297483005763780613"

async def sort_roles(server):
    """
    Sort roles alphabetically
    """
    start_marker_role = get_role_by_id(server, POS_START)
    end_marker_role = get_role_by_id(server, POS_END)

    if not start_marker_role:
        print("Could not get start marker role")
        return

    if not end_marker_role:
        print("Could not get end marker role")
        return

    # Get all roles
    rlist = {}
    for chan in chain(server.get_chans_in_cat(PUB_CAT), server.get_chans_in_cat(PRV_CAT)):
        rlist["%s-op" % chan.name] = \
            get_role_by_name(server, "%s-op" % chan.name)

        rlist["%s-member" % chan.name] = \
            get_role_by_name(server, "%s-member" % chan.name)

    # Sort them and position
    crt_pos = start_marker_role.position - 1
    for rname in sorted(rlist.keys()):
        await rlist[rname].set_position(crt_pos)
        crt_pos -= 1

    # Position the end marker
    await end_marker_role.set_position(crt_pos)

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
        await chans[cname].set_position(min_pos)
        min_pos += 1

async def resync_roles(server):
    """
    Go over all channels and set roles according to op/user access procedure
    """
    for chan in server.get_chans_in_cat(PUB_CAT):
        await chan.set_op_role("%s-op" % chan.name)

    for chan in server.get_chans_in_cat(PRV_CAT):
        await chan.set_op_role("%s-op" % chan.name)
        await chan.set_standard_role("%s-member" % chan.name)

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
    user = get_user_by_id(server, str_to_id(text[2]))

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

    if chtype == PUB_CAT:
        await server.create_text_channel(chname, PUB_CAT)
    elif chtype == PRV_CAT:
        await server.create_text_channel(chname, PRV_CAT)

    await server.create_role(
        "%s-op" % chname,
        mentionable=True)

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
        get_role_by_name(server, "%s-op" % chan.name))
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

    chdata = str_to_id(text[0])
    for chan in server.get_chans_in_cat(PUB_CAT):
        if chan.name == chdata or chan.id == chdata:
            await chan.set_category_name(PRV_CAT)
            await sort_chans(server, PRV_CAT)

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

    chdata = str_to_id(text[0])
    for chan in server.get_chans_in_cat(PRV_CAT):
        if chan.name == chdata or chan.id == chdata:
            await chan.set_category_name(PUB_CAT)
            await sort_chans(server, PUB_CAT)
            # Delete role
            await server.delete_role_by_name("%s-member" % chan.name)

            await resync_roles(server)

            reply("Done!")
            return

    reply("No private channel named %s" % chdata)

@hook.command(server_id=SRV)
def list_chans(server):
    """
    Print a list of channels
    """
    resp = "```\nPublic channels:\n"
    for chan in server.get_chans_in_cat(PUB_CAT):
        if chan.topic:
            resp += "%s - %s\n" % (chan.name, chan.topic)
        else:
            resp += "%s\n" % chan.name

    resp += "Private channels:\n"
    for chan in server.get_chans_in_cat(PRV_CAT):
        if chan.topic:
            resp += "%s - %s\n" % (chan.name, chan.topic)
        else:
            resp += "%s\n" % chan.name

    resp += "```"
    return resp

@hook.command(server_id=SRV)
def join(text, server, reply, event, send_message):
    """
    <channel> - join a private channel
    """
    text = text.split(" ")
    if len(text) != 1:
        reply("Please input a valid channel name")
        return

    # Lookup channel
    chdata = str_to_id(text[0])
    target_chan = None
    for chan in server.get_chans_in_cat(PRV_CAT):
        if chan.name == chdata or chan.id == chdata:
            target_chan = chan
            break

    # Check if it's public
    if target_chan == None:
        for chan in server.get_chans_in_cat(PUB_CAT):
            if chan.name == chdata or chan.id == chdata:
                return "Channel %s is already public. You can view it as is." % chan.name

    # Check for rights
    has_right = False
    for urole in event.author.roles:
        if urole.name in REQUIRED_ACCESS_ROLES:
            has_right = True

        if urole.name == NSFW_FORBID_ROLE and target_chan.is_nsfw:
            return "You can't join a NSFW channel."

    if not has_right:
        return "You don't have the minumum rights to use this command."

    # Add the role
    event.author.add_role(
        get_role_by_name(server, "%s-member" % target_chan.name))

    # Announce on the channel
    send_message("Joins <@%s>" % event.author.id, target=chan.id)
    event.msg.add_reaction("👍")

@hook.command(server_id=SRV)
def part(server, reply, event, send_message):
    """
    <channel> - part a private channel
    """
    chan_id = event.channel.id
    for chan in server.get_chans_in_cat(PRV_CAT):
        if chan.id == chan_id:
            event.author.remove_role(
                get_role_by_name(server, "%s-member" % chan.name))
            send_message("Part <@%s>" % event.author.id, target=chan.id)
            event.msg.add_reaction("👍")

    for chan in server.get_chans_in_cat(PUB_CAT):
        if chan.id == chan_id:
            return "Channel %s is already public. It can't be parted." % chan.name

def find_irc_chan(server, chan_name=None, chan_id=None):
    if not chan_name and not chan_id:
        print("Needs one of name or id")
        return None

    for chan in chain(server.get_chans_in_cat(PUB_CAT), server.get_chans_in_cat(PRV_CAT)):
        if chan.id == chan_id or chan.name == chan_name:
            return chan

    return None

def user_has_role(user, role_name):
    for urole in user.roles:
        if urole.name == role_name:
            return True

    return False

@hook.command(server_id=SRV)
def set_topic(server, reply, event, text):
    """
    <topic> - set channel topic (only channel OPs can do it)
    """

    target_chan = find_irc_chan(server, chan_id=event.channnel.id)
    if not target_chan:
        return "You're not in a user managed channel"

    # Check if user is OP
    has_right = user_has_role(
        event.author,
        "%s-op" % target_chan.name)

    if not has_right:
        return "Only channel OPs can do that"

    if "NSFW" not in text:
        text += " [NSFW]"

    target_chan.set_topic(text)

@hook.command(server_id=SRV)
def make_nsfw(server, reply, event, text, send_message):
    """
    <topic> - make channel NSFW (only channel OPs can do it)
    """

    target_chan = find_irc_chan(server, chan_id=event.channnel.id)
    if not target_chan:
        return "You're not in a user managed channel"

    # Check if user is OP
    has_right = user_has_role(
        event.author,
        "%s-op" % event.channel.name)

    if not has_right:
        return "Only channel OPs can do that"

    # Set NSFW
    target_chan.set_nsfw(True)

    # Add NSFW to topic
    if "NSFW" not in target_chan.topic:
        target_chan.set_topic(text + " [NSFW]")

    # Purge non-NSFW users
    member_role = get_role_by_name(server, "%s-member" % target_chan.name)
    for user in target_chan.members_accessing_chan():
        for urole in user.roles:
            if urole.name == NSFW_FORBID_ROLE:
                user.remove_role(member_role)
                send_message("Part <@%s> - because channel was made NSFW" %
                    user.id, target=target_chan.id)

                user.send_pm("You have been removed from %s, because the channel was made NSFW." %
                    target_chan.name)

@hook.command(server_id=SRV)
def make_sfw(server, reply, event, text):
    """
    <topic> - make channel SFW (only channel OPs can do it)
    """

    target_chan = find_irc_chan(server, chan_id=event.channnel.id)
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