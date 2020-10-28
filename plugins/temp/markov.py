import markovify

from plugins.log import get_msgs_for_user_in_chan, get_msgs_in_chan
from utils.discord_utils import str_to_id, get_channel_by_id
from core import hook

MSG_LIMIT = 10000


@hook.command()
def markov(server, text, event):
    """
    <user channel> - Generate sentence using a markov chain for a user using data from the given channel.
    If no user is specified, a sentence will be generated using all user messages.
    """
    # Parse input
    text = text.split(" ")
    chan_id = ""
    user = ""
    if len(text) == 2:
        user = str_to_id(text[0]).strip()
        chan_id = str_to_id(text[1]).strip()
    elif len(text) == 1:
        chan_id = str_to_id(text[0]).strip()
    else:
        return "Needs at least a channel (e.g. `.markov #chan`) or a user and a channel (e.g. `.markov @user #channel`)"

    chan = get_channel_by_id(server, chan_id)
    if not chan:
        return "Given parameter is not a channel. Help:\n%s" % markov.__doc__

    author_has_access = False
    for user_acc in chan.members_accessing_chan():
        if event.author.id == user_acc.id:
            author_has_access = True
            break

    if not author_has_access:
        return "Invalid channel."

    # Get data
    msg_list = []
    if user == "":
        msg_list = get_msgs_in_chan(chan.id, MSG_LIMIT)
    else:
        msg_list = get_msgs_for_user_in_chan(user, chan.id, MSG_LIMIT)

    msg_list = list(set(msg_list))
    if len(msg_list) == 0:
        return "Could get data"

    print("Got %d messages" % len(msg_list))
    # Remove short messages
    for idx, msg in enumerate(msg_list):
        msg_split = set(msg.split())
        if len(msg_split) < 6:
            msg_list.pop(idx)

    print("Inputting %d messages" % len(msg_list))
    text_model = markovify.NewlineText(
        "\n".join(msg_list), retain_original=False)

    return "```%s```" % text_model.make_short_sentence(min_chars=50, max_chars=300, tries=10000, DEFAULT_MAX_OVERLAP_RATIO=0.4)
