import base64
import requests
import os

from urllib.parse import urlparse
from spanky.plugin import hook
from spanky.hook2 import Hook, ComplexCommand
from spanky.utils import discord_utils as dutils
from spanky.plugin.permissions import Permission

FETCH_SERVICE = None

@hook.on_start()
def load_fetch_service(bot):
    global FETCH_SERVICE

    if "fetch_service" in bot.config:
        FETCH_SERVICE = bot.config["fetch_service"]

    print(f"Using fetch service at {FETCH_SERVICE}")

@hook.command()
def tt(text):
    text = text.strip()

    # Check if it's a tiktok url
    result = urlparse(text)

    if "tiktok.com" not in result.netloc:
        return "Not a tiktok url"

    # Fetch the video from FETCH_SERVICE
    encoded_url = base64.b64encode(text.encode("utf-8")).decode("utf-8")

    print(encoded_url)

    url = f"{FETCH_SERVICE}/tiktok/{encoded_url}"

    r = requests.get(url)
    if r.status_code != 200:
        return False, "Error fetching video"

    return True, r.content

@hook.command()
def igram(text):
    text = text.strip()

    # Check if it's a tiktok url
    result = urlparse(text)

    if "instagram.com" not in result.netloc:
        return "Not a tiktok url"

    # Fetch the video from FETCH_SERVICE
    encoded_url = base64.b64encode(text.encode("utf-8")).decode("utf-8")

    print(text, encoded_url)

    url = f"{FETCH_SERVICE}/instagram/{encoded_url}"

    r = requests.get(url)
    if r.status_code != 200:
        return False, "Error fetching video"

    return True, r.content


# # Twitter commands
# RODDIT_ID = "287285563118190592"
# hook = Hook("twitter")
# twitter = ComplexCommand(hook, "twitter",  permissions=Permission.admin, server_id=[RODDIT_ID])


# def get_tweets(name):
#     url = f"{FETCH_SERVICE}/twitter/{name}"
#     r = requests.get(url)
#     if r.status_code != 200:
#         return None

#     return r.json()

# @twitter.subcommand(name="fetch")
# def fetch(text, send_message, storage):
#     """
#     Fetch tweets for an account
#     """
#     r = get_tweets(text)
#     if r is None:
#         return "Error fetching tweets"

#     if "history" not in storage:
#         storage["history"] = {}

#     if text not in storage["history"]:
#         storage["history"][text] = []

#     for tweet in r["links"]:
#         if tweet in storage["history"][text]:
#             continue
#         storage["history"][text].append(tweet)

#         send_message(f"https://vxtwitter.com{tweet}")

#     storage.sync()


# @hook.periodic(600)
# def check_tweets(bot, storage_getter, send_message):
#     storage = storage_getter(RODDIT_ID, "twitter")

#     if "channels" not in storage:
#         return

#     server = None
#     for srv in bot.get_servers():
#         if srv.id == RODDIT_ID:
#             server = srv
#             break

#     for chan_id, accounts in storage["channels"].items():
#         def target_send_message(msg):
#             send_message(msg, target=chan_id, server=server)

#         for acc in accounts:
#             print("Fetching tweets for", acc)
#             fetch(acc, target_send_message, storage)


# @twitter.subcommand(name="add")
# def add(server, text, storage):
#     """
#     Add a twitter account to the list:
#     <account> <channel>
#     """
#     text = text.strip().split(" ")
#     if len(text) != 2:
#         return "Invalid syntax: add <account> <channel>"

#     account = text[0]
#     chan_id = text[1]

#     # Check that the channel is valid
#     try:
#         chan_id = dutils.str_to_id(chan_id)

#         channel = dutils.get_channel_by_id(server, chan_id)
#         if channel is None:
#             return "Could not find channel"

#     except Exception as e:
#         return "Invalid channel"

#     valid_tweets = get_tweets(account)
#     try:
#         if len(valid_tweets["links"]) == 0:
#             return "Account doesn't exist"
#     except Exception as e:
#         return "General error: " + str(e)

#     if "channels" not in storage:
#         storage["channels"] = {}

#     if chan_id not in storage["channels"]:
#         storage["channels"][chan_id] = []

#     if account not in storage["channels"][chan_id]:
#         storage["channels"][chan_id].append(account)
#         storage.sync()
#         return "Added account"
#     else:
#         return "Account already added"

# @twitter.subcommand(name="remove")
# def remove(text, storage):
#     """
#     Remove a twitter account from the list:
#     <account> <channel>
#     """
#     text = text.strip().split(" ")
#     if len(text) != 2:
#         return "Invalid syntax: add <account> <channel>"

#     account = text[0]
#     chan_id = text[1]

#     if "channels" not in storage:
#         return "No accounts added"

#     if chan_id not in storage["channels"]:
#         return "No accounts added for this channel"

#     if account not in storage["channels"][chan_id]:
#         return "Account not added"

#     storage["channels"][chan_id].remove(account)
#     storage.sync()
#     return "Removed account"


# @twitter.subcommand(name="list")
# def list_accounts(storage):
#     """
#     List all accounts
#     """
#     if "channels" not in storage:
#         return "No accounts added"

#     msg = ""
#     for chan_id, accounts in storage["channels"].items():
#         msg += f"\nChannel: <#{chan_id}>: "
#         for acc in accounts:
#             msg += f"`{acc}` "

#     return msg