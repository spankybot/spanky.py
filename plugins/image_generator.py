import itertools
import praw
import random

import spanky.utils.time_utils as tutils
from spanky.plugin.permissions import Permission

from spanky.hook2 import Hook, EventType, Command

hook = Hook("image_generator", storage_name="plugins_image_generator")


RODDIT_ID = "287285563118190592"
TESTOSTERON = "611894947024470027"
ROBYTE = "464089471806210049"
BEN_SRV = "484640057764872193"
DISO_SRV = "423964901128536065"
TZ_SRV = "754550072955371620"
TZ_SRV2 = "426392328429633542"
TZ_SRV3 = "881138853765865493"
TZ_SRV4 = "905470387717021696"
DRUNKBOYZ_SRV = "418705572511219723"
CNC_TEST_SRV = "648937029433950218"


SERVERS = [
    RODDIT_ID,
    TESTOSTERON,
    ROBYTE,
    BEN_SRV,
    DISO_SRV,
    TZ_SRV,
    TZ_SRV2,
    TZ_SRV3,
    TZ_SRV4,
    DRUNKBOYZ_SRV,
    CNC_TEST_SRV,
]

USER_AGENT = "Image fetcher for Snoonet:#Romania by /u/programatorulupeste"
domains = [
    "imgur.com",
    "gfycat.com",
    "redditmedia.com",
    "i.redd.it",
    "v.redd.it",
    "flic.kr",
    "500px.com",
    "redgifs.com",
]

dont_cache = ["random", "randnsfw"]

reddit_inst = None
ustorage = None
UPDATE_TIMEOUT = 60 * 60 * 6  # 6 hours
tracked_subs = []


def get_links_from_sub(reddit, sub, top_type):
    try:
        subreddit = reddit.subreddit(sub)

        new_links = []
        for top in top_type:
            for submission in subreddit.top(top):
                if submission.is_self:
                    continue

                for domain in domains:
                    if domain in submission.url:
                        # Embeds don't work with v.redd.it
                        if "https://v.redd.it" not in submission.url:
                            new_links.append(f"{submission.id};{submission.url}")
                        else:
                            new_links.append(
                                f"{submission.id};https://reddit.com{submission.permalink}"
                            )
                        break

        return new_links
    except Exception as e:
        print(e)
        return []


def update_sub(reddit, sub, ustorage):
    print(f"updating {sub}")

    if sub not in dont_cache:
        links = get_links_from_sub(
            reddit, sub, ["day", "week", "month", "year"]
        )

        if sub not in ustorage["data"]:
            ustorage["data"][sub] = {
                "links": links,
                "updated_on": tutils.tnow(),
            }
        else:
            ustorage["data"][sub]["links"].extend(links)
            ustorage["data"][sub]["updated_on"] = tutils.tnow()

        # filter out duplicates
        ustorage["data"][sub]["links"] = list(
            set(ustorage["data"][sub]["links"])
        )
        ustorage.sync()

        return ustorage["data"][sub]["links"]
    else:
        return get_links_from_sub(reddit, sub, ["month"])

@hook.event(EventType.on_start)
def init(bot, unique_storage):
    global reddit_inst

    auth = bot.config.get("reddit_auth")
    reddit_inst = praw.Reddit(
        client_id=auth.get("client_id"),
        client_secret=auth.get("client_secret"),
        username=auth.get("username"),
        password=auth.get("password"),
        user_agent="Subreddit watcher by /u/programatorulupeste",
    )

    global ustorage
    ustorage = unique_storage

    if "data" not in ustorage:
        ustorage["data"] = {}

    ustorage.sync()


@hook.periodic(60 * 60 * 12)
def update_porn():
    for sub in ustorage["data"].keys():
        if tutils.tnow() - ustorage["data"][sub]["updated_on"] > UPDATE_TIMEOUT:
            update_sub(reddit_inst, sub, ustorage)


@hook.command(server_id=SERVERS, permissions=Permission.admin)
def force_refresh_porn(text):
    if text != "":
        if text in ustorage["data"]:
            update_sub(reddit_inst, text, ustorage)
            return "Done."
        else:
            return "No such sub."

    for sub in ustorage["data"].keys():
        update_sub(reddit_inst, sub, ustorage)


@hook.command(server_id=SERVERS, permissions=Permission.admin)
def nuke_porn(text):
    if text != "":
        if text in ustorage["data"]:
            del ustorage["data"][text]
            update_sub(reddit_inst, text, ustorage)
            return "Done."
        else:
            return "No such sub."


def get_links_from_subs(sub_list):
    data = []
    for sub in sub_list:
        if sub in ustorage["data"]:
            data.extend(ustorage["data"][sub]["links"])
        else:
            data.extend(update_sub(reddit_inst, sub, ustorage))

    return random.choice(data)


def format_output_message(data):
    data = data.split(";", maxsplit=1)
    link = data[1]
    source = data[0]

    if "gfycat.com" in link:
        redgif = link.replace("gfycat.com", "gifdeliverynetwork.com")
        link = "%s %s" % (redgif, link)

    return "%s / source: <https://redd.it/%s>" % (link, source)


# @hook.on_connection_ready
# def cache_all():
#     for sub in tracked_subs:
#         if sub in dont_cache:
#             continue

#         print("PRECACHING " + sub)

#         if sub not in ustorage["data"].keys():
#             update_sub(reddit_inst, sub, ustorage)
#         else:
#             if (
#                 tutils.tnow() - ustorage["data"][sub]["updated_on"]
#                 > UPDATE_TIMEOUT
#             ):
#                 update_sub(reddit_inst, sub, ustorage)

@hook.command(server_id=SERVERS)
def fetch_image(text):
    if text:
        text = text.split()
        data = get_links_from_subs(text)

        return format_output_message(data)
    else:
        return "Please specify a sub or a list of subs (e.g.: .fetch_image RomaniaPorn or .fetch_image RomaniaPorn RoGoneWild)"


commands = {
    "skinny": ["skinnytail"],
    "roscate": ["ginger", "redheads", "RedheadGifs"],
    "tatuate": ["altgonewild"],
    "nsfwfunny": ["nsfwfunny"],
    "craci": ["thighhighs", "stockings"],
    "buci": ["ass", "asstastic", "assinthong", "pawg", "SuperDuperAss"],
    "tzatze": ["boobs", "boobies", "BiggerThanYouThought"],
    "fetish": ["kinky", "bdsm", "bondage", "collared"],
    "teen": ["LegalTeens", "Just18", "youngporn", "barelylegal"],
    "sloboz": ["cumsluts", "GirlsFinishingTheJob"],
    "anal": ["anal", "painal"],
    "milf": ["milf"],
    "amateur": ["RealGirls", "Amateur", "GoneWild"],
    "traps": ["Tgirls", "traps", "gonewildtrans", "tgifs"],
    "aww": ["aww"],
    "pisi": ["cats"],
    "cutu": ["dogpictures", "TuckedInPuppies"],
    "blep": ["blep", "blop"],
    "capre": ["doggy"],
    "lesbiene": ["dykesgonewild"],
    "thicc": ["pawg", "thick"],
    "asians": ["AsianNSFW", "AsianPorn", "AsianHotties"],
    "raton": ["TrashPandas"],
    "plsporn": ["randnsfw", "The_Best_NSFW_GIFS"],
    "plsgayporn": [
        "AmateurGayPorn",
        "DickPics4Freedom",
        "foreskin",
        "GaybrosGoneWild",
        "gayporn",
        "MassiveCock",
        "penis",
        "ratemycock",
        "selfservice",
        "totallystraight",
    ],
    "blonde": [
        "Blonde",
        "blondegirlsfucking",
        "nsfwblondeporn",
        "GoneWildBlondes",
        "blondehairblueeyes",
    ],
    "femboy": ["femboy", "femboys"],
    "thot": ["tiktokthots"],
}

@hook.event(EventType.on_start)
def init_porn_cmds():
    for cmd_name, subs in commands.items():
        global tracked_subs
        tracked_subs.extend(subs)
        tracked_subs = list(set(tracked_subs))

        def gen_wrapper(subs):
            def wrapper():
                data = get_links_from_subs(subs)
                return format_output_message(data)
            return wrapper
        
        hook.add_command(Command(hook, cmd_name, gen_wrapper(subs), server_id=SERVERS))
