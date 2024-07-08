import random
import nextcord
import spanky.utils.discord_utils as dutils
import spanky.utils.time_utils as tutils

from spanky.plugin.permissions import Permission
from spanky.hook2 import (
    Hook,
    ComplexCommand,
)

hook = Hook("spamfun", storage_name="plugins_spamfun.json")
chanhook = ComplexCommand(hook, "spamfun")


@chanhook.subcommand(permissions=Permission.admin)
def chan_set(event, storage, text):
    """
    Set the channel to spam in.
    """
    if "spamfun" not in storage:
        storage["spamfun"] = {}

    channel = dutils.get_channel_by_id_or_name(event.server, text)

    if channel is None:
        return "Channel not found"

    storage["spamfun"]["channel"] = channel.id
    storage.sync()

    return f"Set channel to <#{channel.id}>"

@chanhook.subcommand(permissions=Permission.admin)
def chan_unset(storage):
    """
    Unset the channel to spam in.
    """
    storage["spamfun"]["channel"] = None
    storage.sync()

    return "Unset channel"

@chanhook.subcommand(permissions=Permission.admin)
def chan_get(storage):
    """
    Get the channel to spam in.
    """
    if "spamfun" not in storage:
        return "No channel set"

    if "channel" not in storage["spamfun"]:
        return "No channel set"

    return f"Channel is <#{storage['spamfun']['channel']}>"

# # Trivia commands
# @chanhook.subcommand()
# def start_trivia(event, storage):
#     """
#     Start trivia.
#     """
#     if "spamfun" not in storage:
#         storage["spamfun"] = {}

#     storage["spamfun"]["trivia_started"] = tutils.tnow()
#     storage.sync()

#     return "Trivia started"

# Duck hunt commands
@chanhook.subcommand(permissions=Permission.admin)
def duckhunt_start(event, storage):
    """
    Start duck hunt.
    """
    if "spamfun" not in storage:
        return "No channel set. Use `.spamfun chan_set` to set the channel."
    
    if "channel" not in storage["spamfun"]:
        return "No channel set. Use `.spamfun chan_set` to set the channel."

    storage["spamfun"]["duckhunt_started"] = tutils.tnow()
    storage["spamfun"]["next_duck"] = tutils.tnow() + random.randint(60, 300)
    storage["spamfun"]["needs_hunt"] = False
    storage.sync()

    return "Duck hunt started"

@chanhook.subcommand(permissions=Permission.admin)
def duckhunt_stop(event, storage):
    """
    Stop duck hunt.
    """
    if "spamfun" not in storage:
        return "No channel set. Use `.spamfun chan_set` to set the channel."
    
    if "channel" not in storage["spamfun"]:
        return "No channel set. Use `.spamfun chan_set` to set the channel."

    storage["spamfun"]["duckhunt_started"] = None
    storage.sync()

    return "Duck hunt stopped"

@chanhook.subcommand(permissions=Permission.admin)
def duckhunt_get(event, storage):
    """
    Get duck hunt.
    """
    if "spamfun" not in storage:
        return "No channel set. Use `.spamfun chan_set` to set the channel."
    
    if "channel" not in storage["spamfun"]:
        return "No channel set. Use `.spamfun chan_set` to set the channel."

    if "duckhunt_started" not in storage["spamfun"]:
        return "Duck hunt not started"

    if storage["spamfun"]["duckhunt_started"] is None:
        return "Duck hunt not started"

    return f"Duck hunt started at {tutils.time_to_date(storage['spamfun']['duckhunt_started'])}"


words = [
    "quack",
    "mac mac",
    "hatz johnule",
    "iote ratza",
]
emojis = [
    "🦆",
    # gun emoji
    "🔫",
    # duck emoji
    "🦆",
    # explosion emoji
    "💥",
    # dead emoji
    "💀",
    # skull emoji
    "☠️",
    # steak emoji
    "🥩",
    # meat emoji
    "🍖",
]

def compose_duck_message():
    word = random.choice(words)

    word_split = word.split(" ")

    # add between 1 and 3 emojis after each word
    for i in range(len(word_split)):
        if i == 0:
            word_split[i] = random.choice(emojis) + " " + word_split[i]

        word_split[i] += " " + " ".join(random.choices(emojis, k=random.randint(1, 3)))

    return " ".join(word_split)

def send_duck(storage, send_message, server):
    if "spamfun" not in storage:
        return "No channel set. Use `.spamfun chan_set` to set the channel."
    
    if "channel" not in storage["spamfun"]:
        return "No channel set. Use `.spamfun chan_set` to set the channel."

    if "duckhunt_started" not in storage["spamfun"]:
        return "Duck hunt not started"

    if storage["spamfun"]["duckhunt_started"] is None:
        return "Duck hunt not started"
    
    if tutils.tnow() < storage["spamfun"]["next_duck"]:
        return "Not time to send a duck yet"
    
    if storage["spamfun"]["needs_hunt"]:
        return "Duck hunt is needed"

    msg = compose_duck_message()

    # Set the next duck to be sent in 60-300 seconds
    storage["spamfun"]["next_duck"] = tutils.tnow() + random.randint(60, 300)
    storage["spamfun"]["needs_hunt"] = True
    storage.sync()
    send_message(msg, target=storage["spamfun"]["channel"], server=server, check_old=False)


@chanhook.subcommand(permissions=Permission.admin)
def emit_duck(send_message, storage, server):
    """
    Emit a duck.
    """
    return send_duck(storage, send_message, server)

@hook.periodic(3)
def emit_timed_duck(bot, send_message, storage_getter):
    """
    Emit a duck every 10 seconds.
    """

    for server in bot.get_servers():
        storage = storage_getter(server.id, "plugins_spamfun.json")

        if "spamfun" not in storage:
            continue
        
        send_duck(storage, send_message, server)

duck_shot = [
    "i-ai dat in cap",
    "bravo boss",
    "bine asa",
]
@hook.command()
def bang(send_message, storage, server, event):
    """
    Bang bang.
    """
    if "spamfun" not in storage:
        return
    
    if "channel" not in storage["spamfun"]:
        return
    
    if event.channel.id != storage["spamfun"]["channel"]:
        return "No bangs here"

    if "duckhunt_started" not in storage["spamfun"]:
        return "Duck hunt not started"

    if storage["spamfun"]["duckhunt_started"] is None:
        return "Duck hunt not started"

    if not storage["spamfun"]["needs_hunt"]:
        return "No duck to hunt"
    
    if "duckhunt_score" not in storage["spamfun"]:
        storage["spamfun"]["duckhunt_score"] = {}

    storage["spamfun"]["duckhunt_score"][event.author.id] = storage["spamfun"]["duckhunt_score"].get(event.author.id, 0) + 1
    storage["spamfun"]["needs_hunt"] = False
    storage["spamfun"]["next_duck"] = tutils.tnow() + random.randint(60, 300)
    storage.sync()

    return random.choice(duck_shot) + f" - ai {storage['spamfun']['duckhunt_score'][event.author.id]} puncte"

@chanhook.subcommand()
def duck_score(storage, send_message):
    """
    Get duck score.
    """
    if "spamfun" not in storage:
        return "No channel set. Use `.spamfun chan_set` to set the channel."
    
    if "channel" not in storage["spamfun"]:
        return "No channel set. Use `.spamfun chan_set` to set the channel."

    if "duckhunt_score" not in storage["spamfun"]:
        return "No duck score"

    send_message(
        "\n".join([f"<@{k}>: {v}" for k, v in storage["spamfun"]["duckhunt_score"].items()]),
        allowed_mentions=nextcord.AllowedMentions.none())