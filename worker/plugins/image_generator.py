import os
import praw
import random

from SpankyWorker import hook
import SpankyCommon.utils.time_utils as tutils

RODDIT_ID = 287285563118190592
FLR_SERVER = 573566494332420123
TESTOSTERON = 611894947024470027
ROBYTE = 464089471806210049
BEN_SRV = 484640057764872193
DISO_SRV = 423964901128536065
TEST_SRV = 297483005763780613

SERVERS = [
    RODDIT_ID,
    FLR_SERVER,
    TESTOSTERON,
    ROBYTE,
    BEN_SRV,
    DISO_SRV,
    TEST_SRV,
]

USER_AGENT = "Image fetcher for Snoonet:#Romania by /u/programatorulupeste"
domains = [
    "imgur.com",
    "gfycat.com",
    "redditmedia.com",
    "i.redd.it",
    "flic.kr",
    "500px.com",
    "redgifs.com",
]

dont_cache = ["random", "randnsfw"]
gstorage = None


def get_links_from_sub(r, sub):
    subreddit = r.subreddit(sub)

    new_links = []
    # Get last months submissions
    for submission in subreddit.top("month"):
        # Skip self submissions
        if not submission.is_self:
            # If domain is valid
            for domain in domains:
                if domain in submission.url:
                    # Append it
                    new_links.append((submission.url, submission.id))
                    break

    return new_links


def refresh_cache(r, sub):
    # Get new links
    new_links = get_links_from_sub(r, sub)

    # Update storage
    gstorage["links"][sub] = new_links
    gstorage["cachetime"][sub] = tutils.tnow()

    gstorage.sync()


def del_sub(sub):
    print("Removing sub %s" % sub)
    if sub in gstorage["links"]:
        del gstorage["links"][sub]

    if sub in gstorage["cachetime"]:
        del gstorage["cachetime"][sub]

    gstorage.sync()


def get_links_from_subs(sub_list):
    data = []
    r = praw.Reddit("irc_bot", user_agent=USER_AGENT)

    now = tutils.tnow()

    for sub in sub_list:
        # If it's in the no cache list, just get links
        if sub in dont_cache:
            print("%s is in no cache list" % sub)
            data = get_links_from_sub(r, sub)
            continue

        # If it's a new subreddit initialize it
        if sub not in gstorage["links"].keys():
            gstorage["links"][sub] = []
            gstorage["cachetime"][sub] = 0

        # Cache older than 2 hours?
        if now - gstorage["cachetime"][sub] > 7200:
            try:
                refresh_cache(r, sub)
            except Exception as e:
                print(e)
                del_sub(sub)
                return ["Error :/"]

        data.extend(gstorage["links"][sub])
        if len(data) == 0:
            for el in sub:
                del_sub(el)

    return data


@hook.on_start(unique_storage=True)
def init(storage):
    with open(os.path.realpath(__file__)) as f:
        data = f.read()

    if "cachetime" not in storage:
        storage["cachetime"] = {}

    if "links" not in storage:
        storage["links"] = {}

    global gstorage
    gstorage = storage

    data = data.replace(" ", "")
    data = data.replace("\n", "")
    data = data.replace("'", "")
    data = data.replace('"', "")

    # Load this file and pre-cache subreddits
    start = "get_links_from_subs" + "(["
    end = "])"

    startpos = 0
    endpos = 0
    while True:
        startpos = data.find(start, startpos)
        endpos = data.find(end, startpos)

        if startpos == -1:
            break

        subs = data[startpos + len(start) : endpos].split(",")
        get_links_from_subs(subs)

        startpos += len(start)


@hook.periodic(300)
def refresh_porn():
    global gstorage

    for sub in gstorage["links"].keys():
        # Workaround to fool the init that we're not calling anything
        fake_list = [sub]
        get_links_from_subs(fake_list)


@hook.command(server_id=SERVERS)
def force_refresh_porn():
    r = praw.Reddit("irc_bot", user_agent=USER_AGENT)
    db_subs = g_db.execute(select([subs.c.subreddit]))
    for el in db_subs:
        try:
            refresh_cache(r, el["subreddit"])
        except Exception as e:
            print(e)
            pass


def format_output_message(data):
    link, source = random.choice(data)

    if "gfycat.com" in link:
        redgif = link.replace("gfycat.com", "gifdeliverynetwork.com")
        link = "%s %s" % (redgif, link)

    return "%s / source: <https://redd.it/%s>" % (link, source)


@hook.command(server_id=SERVERS)
def skinny():
    data = get_links_from_subs(["skinnytail"])

    return format_output_message(data)


@hook.command(server_id=SERVERS)
def roscate():
    data = get_links_from_subs(["ginger", "redheads", "RedheadGifs"])

    return format_output_message(data)


@hook.command(server_id=SERVERS)
def tatuate():
    data = get_links_from_subs(["altgonewild"])

    return format_output_message(data)


@hook.command(server_id=SERVERS)
def nsfwfunny():
    data = get_links_from_subs(["nsfwfunny"])

    return format_output_message(data)


@hook.command(server_id=SERVERS)
def craci():
    data = get_links_from_subs(["thighhighs", "stockings"])

    return format_output_message(data)


@hook.command(server_id=SERVERS)
def buci():
    data = get_links_from_subs(["ass", "asstastic", "assinthong", "pawg"])

    return format_output_message(data)


@hook.command(server_id=SERVERS)
def tzatze():
    data = get_links_from_subs(["boobs", "boobies", "BiggerThanYouThought"])

    return format_output_message(data)


@hook.command(server_id=SERVERS)
def fetish():
    data = get_links_from_subs(["kinky", "bdsm", "bondage", "collared"])

    return format_output_message(data)


@hook.command(server_id=SERVERS)
def teen():
    data = get_links_from_subs(
        ["LegalTeens", "Just18", "youngporn", "barelylegal"]
    )

    return format_output_message(data)


@hook.command(server_id=SERVERS)
def sloboz():
    data = get_links_from_subs(["cumsluts", "GirlsFinishingTheJob"])

    return format_output_message(data)


@hook.command(server_id=SERVERS)
def anal():
    data = get_links_from_subs(["anal", "painal"])

    return format_output_message(data)


@hook.command(server_id=SERVERS)
def milf():
    data = get_links_from_subs(["milf"])

    return format_output_message(data)


@hook.command(server_id=SERVERS)
def amateur():
    data = get_links_from_subs(["RealGirls", "Amateur", "GoneWild"])

    return format_output_message(data)


@hook.command(server_id=SERVERS)
def traps():
    data = get_links_from_subs(["Tgirls", "traps", "gonewildtrans", "tgifs"])

    return format_output_message(data)


@hook.command(server_id=SERVERS)
def aww():
    data = get_links_from_subs(["aww"])

    return format_output_message(data)


@hook.command(server_id=SERVERS)
def pisi():
    data = get_links_from_subs(["cats"])

    return format_output_message(data)


@hook.command(server_id=SERVERS)
def cutu():
    data = get_links_from_subs(["dogpictures", "TuckedInPuppies"])

    return format_output_message(data) + " HAM, HAM!"


@hook.command(server_id=SERVERS)
def blep():
    data = get_links_from_subs(["blep", "blop"])

    return format_output_message(data) + " :P"


@hook.command(server_id=SERVERS)
def capre():
    data = get_links_from_subs(["doggy"])

    return format_output_message(data) + " NSFW!"


@hook.command(server_id=SERVERS)
def lesbiene():
    data = get_links_from_subs(["dykesgonewild"])

    return format_output_message(data) + " NSFW!"


@hook.command(server_id=SERVERS)
def thicc():
    data = get_links_from_subs(["pawg", "thick"])

    return format_output_message(data) + " NSFW!"


@hook.command(server_id=SERVERS)
def asians():
    data = get_links_from_subs(["AsianNSFW", "AsianPorn", "AsianHotties"])

    return format_output_message(data) + " NSFW!"


@hook.command(server_id=SERVERS)
def raton():
    data = get_links_from_subs(["TrashPandas"])

    return format_output_message(data)


@hook.command(server_id=SERVERS)
def fetch_image(text):
    if text:
        text = text.split()
        data = get_links_from_subs(text)

        return format_output_message(data)
    else:
        return "Please specify a sub or a list of subs (e.g.: .fetch_image RomaniaPorn or .fetch_image RomaniaPorn RoGoneWild)"


@hook.command(server_id=SERVERS)
def plsporn():
    """pls gib porn"""
    return fetch_image("randnsfw")


@hook.command(server_id=SERVERS)
def plsgayporn():
    """pls gib porn"""
    data = get_links_from_subs(
        [
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
        ]
    )

    return format_output_message(data)
