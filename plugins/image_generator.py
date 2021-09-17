import os
import praw
import random
import asyncio
from spanky.plugin import hook
from datetime import datetime
from sqlalchemy import Table, Column, String, PrimaryKeyConstraint, DateTime
from sqlalchemy.sql import select
from spanky import database

RODDIT_ID = "287285563118190592"
TESTOSTERON = "611894947024470027"
ROBYTE = "464089471806210049"
BEN_SRV = "484640057764872193"
DISO_SRV = "423964901128536065"
TZ_SRV = "754550072955371620"
TZ_SRV2 = "426392328429633542"
TZ_SRV3 = "881138853765865493"
DRUNKBOYZ_SRV = "418705572511219723"

SERVERS = [
    RODDIT_ID,
    TESTOSTERON,
    ROBYTE,
    BEN_SRV,
    DISO_SRV,
    TZ_SRV,
    TZ_SRV2,
    TZ_SRV3,
    DRUNKBOYZ_SRV
]

USER_AGENT = "Image fetcher for Snoonet:#Romania by /u/programatorulupeste"
domains = ['imgur.com', 'gfycat.com', 'redditmedia.com',
           'i.redd.it', 'flic.kr', '500px.com', 'redgifs.com']

dont_cache = ['random', 'randnsfw']

g_db = None
reddit_inst = None

links = Table(
    'links',
    database.metadata,
    Column('subreddit', String),
    Column('link', String),
    Column('source', String)
)

subs = Table(
    'subs',
    database.metadata,
    Column('subreddit', String),
    Column('cachetime', DateTime)
)


def get_links_from_sub(r, sub):
    subreddit = r.subreddit(sub)

    new_links = []
    for submission in subreddit.top("month"):
        if not submission.is_self:
            for domain in domains:
                if domain in submission.url:
                    new_links.append((submission.url, submission.id))
                    break

    return new_links


def refresh_cache(r, el):
    #print("Refreshing cache for " + el)
    delete = links.delete(links.c.subreddit == el)
    g_db.execute(delete)
    g_db.commit()

    new_links = get_links_from_sub(r, el)
    #print("Adding %d links" % len(new_links))

    last_fetch = datetime.utcnow()

    # Update db
    for nlink in new_links:
        g_db.execute(links.insert().values(
            subreddit=el, link=nlink[0], source=nlink[1]))

    # Update db timestamp
    g_db.execute(subs.update().where(
        subs.c.subreddit == el).values(cachetime=last_fetch))

    g_db.commit()


def del_sub(sub):
    print("Removing sub %s" % sub)
    g_db.execute(subs.delete().where(subs.c.subreddit == sub))
    g_db.commit()


def get_links_from_subs(sub):
    return _get_links_from_subs(reddit_inst, sub)


def _get_links_from_subs(r, sub):

    now = datetime.utcnow()

    db_sub_list = g_db.execute(subs.select())
    sub_list = {}
    for row in db_sub_list:
        sub_list[row['subreddit']] = row['cachetime']

    data = []
    for el in sub:
        if el in dont_cache:
            print("%s is in no cache list" % el)
            data = get_links_from_sub(r, el)
            continue

        if el not in sub_list:
            g_db.execute(subs.insert().values(
                subreddit=el, cachetime=datetime.min))
            sub_list[el] = datetime.min
            g_db.commit()

        # Cache older than 2 hours?
        if (now - sub_list[el]).total_seconds() > 7200:
            try:
                refresh_cache(r, el)
            except Exception as e:
                print(e)
                del_sub(el)
                return ["Error :/"]
        else:
            pass
            #print("Cache for %s is %i" %(el, (now - sub_list[el]).total_seconds()))

        db_links = g_db.execute(
            select([links.c.link, links.c.source]).where(links.c.subreddit == el))

        for row in db_links:
            data.append((row))

        if len(data) == 0:
            data = ["Got nothing. Will try harder next time."]
            for el in sub:
                del_sub(el)
    return data


@hook.on_start
def init(bot, db):
    global g_db
    global reddit_inst

    auth = bot.config.get("reddit_auth")
    reddit_inst = praw.Reddit(
        client_id=auth.get("client_id"),
        client_secret=auth.get("client_secret"),
        username=auth.get("username"),
        password=auth.get("password"),
        user_agent="Subreddit watcher by /u/programatorulupeste")

    g_db = db
    with open(os.path.realpath(__file__)) as f:
        data = f.read()

    data = data.replace(" ", "")
    data = data.replace("\n", "")
    data = data.replace("\'", "")
    data = data.replace("\"", "")

    start = "get_links_from_subs" + "(["
    end = "])"

    startpos = 0
    endpos = 0
    while True:
        startpos = data.find(start, startpos)
        endpos = data.find(end, startpos)

        if startpos == -1:
            break

        subs = data[startpos + len(start):endpos].split(",")
        get_links_from_subs(subs)

        startpos += len(start)


@hook.periodic(300, single_threaded=True)
def refresh_porn(db):
    global g_db
    g_db = db

    # print("Refreshing...")
    db_subs = g_db.execute(select([subs.c.subreddit]))
    for el in db_subs:
        fake_list = [el['subreddit']]
        get_links_from_subs(fake_list)


@hook.command(server_id=SERVERS)
def force_refresh_porn():
    db_subs = g_db.execute(select([subs.c.subreddit]))
    for el in db_subs:
        try:
            refresh_cache(reddit_inst, el['subreddit'])
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
    data = get_links_from_subs(['skinnytail'])

    return format_output_message(data)


@hook.command(server_id=SERVERS)
def roscate():
    data = get_links_from_subs(['ginger', 'redheads', 'RedheadGifs'])

    return format_output_message(data)


@hook.command(server_id=SERVERS)
def tatuate():
    data = get_links_from_subs(['altgonewild'])

    return format_output_message(data)


@hook.command(server_id=SERVERS)
def nsfwfunny():
    data = get_links_from_subs(['nsfwfunny'])

    return format_output_message(data)


@hook.command(server_id=SERVERS)
def craci():
    data = get_links_from_subs(['thighhighs', 'stockings'])

    return format_output_message(data)


@hook.command(server_id=SERVERS)
def buci():
    data = get_links_from_subs(
        ['ass', 'asstastic', 'assinthong', 'pawg', 'SuperDuperAss'])

    return format_output_message(data)


@hook.command(server_id=SERVERS)
def tzatze():
    data = get_links_from_subs(['boobs', 'boobies', 'BiggerThanYouThought'])

    return format_output_message(data)


@hook.command(server_id=SERVERS)
def fetish():
    data = get_links_from_subs(['kinky', 'bdsm', 'bondage', 'collared'])

    return format_output_message(data)


@hook.command(server_id=SERVERS)
def teen():
    data = get_links_from_subs(
        ['LegalTeens', 'Just18', 'youngporn', 'barelylegal'])

    return format_output_message(data)


@hook.command(server_id=SERVERS)
def sloboz():
    data = get_links_from_subs(['cumsluts', 'GirlsFinishingTheJob'])

    return format_output_message(data)


@hook.command(server_id=SERVERS)
def anal():
    data = get_links_from_subs(['anal', 'painal'])

    return format_output_message(data)


@hook.command(server_id=SERVERS)
def milf():
    data = get_links_from_subs(['milf'])

    return format_output_message(data)


@hook.command(server_id=SERVERS)
def amateur():
    data = get_links_from_subs(['RealGirls', 'Amateur', 'GoneWild'])

    return format_output_message(data)


@hook.command(server_id=SERVERS)
def traps():
    data = get_links_from_subs(['Tgirls', 'traps', 'gonewildtrans', 'tgifs'])

    return format_output_message(data)


@hook.command(server_id=SERVERS)
def aww():
    data = get_links_from_subs(['aww'])

    return format_output_message(data)


@hook.command(server_id=SERVERS)
def pisi():
    data = get_links_from_subs(['cats'])

    return format_output_message(data)


@hook.command(server_id=SERVERS)
def cutu():
    data = get_links_from_subs(['dogpictures', 'TuckedInPuppies'])

    return format_output_message(data) + " HAM, HAM!"


@hook.command(server_id=SERVERS)
def blep():
    data = get_links_from_subs(['blep', 'blop'])

    return format_output_message(data) + " :P"


@hook.command(server_id=SERVERS)
def capre():
    data = get_links_from_subs(['doggy'])

    return format_output_message(data) + " NSFW!"


@hook.command(server_id=SERVERS)
def lesbiene():
    data = get_links_from_subs(['dykesgonewild'])

    return format_output_message(data) + " NSFW!"


@hook.command(server_id=SERVERS)
def thicc():
    data = get_links_from_subs(['pawg', 'thick'])

    return format_output_message(data) + " NSFW!"


@hook.command(server_id=SERVERS)
def asians():
    data = get_links_from_subs(['AsianNSFW', 'AsianPorn', 'AsianHotties'])

    return format_output_message(data) + " NSFW!"


@hook.command(server_id=SERVERS)
def raton():
    data = get_links_from_subs(['TrashPandas'])

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
    data = get_links_from_subs(['randnsfw', 'The_Best_NSFW_GIFS'])

    return format_output_message(data)


@hook.command(server_id=SERVERS)
def plsgayporn():
    """pls gib porn"""
    data = get_links_from_subs(['AmateurGayPorn', 'DickPics4Freedom', 'foreskin', 'GaybrosGoneWild',
                                'gayporn', 'MassiveCock', 'penis', 'ratemycock', 'selfservice', 'totallystraight'])

    return format_output_message(data)


@hook.command(server_id=SERVERS)
def blonde():
    """blonde"""
    data = get_links_from_subs(['Blonde', 'blondegirlsfucking',
                                'nsfwblondeporn', 'GoneWildBlondes', 'blondehairblueeyes'])

    return format_output_message(data)


@hook.command(server_id=SERVERS)
def femboy():
    """femboy"""
    data = get_links_from_subs(['femboy', 'femboys'])

    return format_output_message(data)
