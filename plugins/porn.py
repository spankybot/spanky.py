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

USER_AGENT = "Image fetcher for Snoonet:#Romania by /u/programatorulupeste"
domains = ['imgur.com', 'gfycat.com', 'redditmedia.com', 'i.redd.it', 'flic.kr', '500px.com']

dont_cache = ['random', 'randnsfw']

g_db = None

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

    new_links =  get_links_from_sub(r, el)
    #print("Adding %d links" % len(new_links))

    last_fetch = datetime.utcnow()

    # Update db
    for nlink in new_links:
        g_db.execute(links.insert().values(subreddit=el, link=nlink[0], source=nlink[1]))

    # Update db timestamp
    g_db.execute(subs.update().where(subs.c.subreddit == el).values(cachetime=last_fetch))

    g_db.commit()


def del_sub(sub):
    print("Removing sub %s" % sub)
    g_db.execute(subs.delete().where(subs.c.subreddit == sub))
    g_db.commit()

def get_links_from_subs(sub):
    try:
        return _get_links_from_subs(sub)
    except:
        import traceback
        traceback.print_exc()
        return("My owner is too dumb to fix me. Please try again")

def _get_links_from_subs(sub):
    data = []
    r = praw.Reddit("irc_bot", user_agent=USER_AGENT)

    now = datetime.utcnow()

    db_sub_list = g_db.execute(subs.select())
    sub_list = {}
    for row in db_sub_list:
        sub_list[row['subreddit']] = row['cachetime']

    for el in sub:
        if el in dont_cache:
            print("%s is in no cache list" % el)
            data = get_links_from_sub(r, el)
            continue

        if el not in sub_list:
            g_db.execute(subs.insert().values(subreddit=el, cachetime=datetime.min))
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

        db_links = g_db.execute(select([links.c.link, links.c.source]).where(links.c.subreddit == el))

        for row in db_links:
            data.append((row))

        if len(data) == 0:
            data = ["Got nothing. Will try harder next time."]
            for el in sub:
                del_sub(el)
    return data

@hook.on_start
def init(db):
    global g_db
    g_db = db
    with open(os.path.realpath(__file__)) as f:
        data = f.read()

    data = data.replace(" ", "")
    data = data.replace("\n","")
    data = data.replace("\'","")
    data = data.replace("\"","")

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

    #print("Refreshing...")
    db_subs = g_db.execute(select([subs.c.subreddit]))
    for el in db_subs:
        fake_list = [el['subreddit']]
        get_links_from_subs(fake_list)

@hook.command(server_id=RODDIT_ID)
def force_refresh_porn():
    r = praw.Reddit("irc_bot", user_agent=USER_AGENT)
    db_subs = g_db.execute(select([subs.c.subreddit]))
    for el in db_subs:
        try:
            refresh_cache(r, el['subreddit'])
        except Exception as e:
            print(e)
            pass

def format_output_message(data):
    entry = random.choice(data)
    return "%s / source: <https://redd.it/%s>" % (entry[0], entry[1])

@hook.command(server_id=RODDIT_ID)
def skinny():
    data = get_links_from_subs(['skinnytail'])

    return format_output_message(data)

@hook.command(server_id=RODDIT_ID)
def roscate():
    data = get_links_from_subs(['ginger', 'redheads', 'RedheadGifs'])

    return format_output_message(data)

@hook.command(server_id=RODDIT_ID)
def tatuate():
    data = get_links_from_subs(['altgonewild'])

    return format_output_message(data)

@hook.command(server_id=RODDIT_ID)
def nsfwfunny():
    data = get_links_from_subs(['nsfwfunny'])

    return format_output_message(data)

@hook.command(server_id=RODDIT_ID)
def craci():
    data = get_links_from_subs(['thighhighs', 'stockings'])

    return format_output_message(data)

@hook.command(server_id=RODDIT_ID)
def buci():
    data = get_links_from_subs(['ass', 'asstastic', 'assinthong', 'pawg'])

    return format_output_message(data)

@hook.command(server_id=RODDIT_ID)
def tzatze():
    data = get_links_from_subs(['boobs', 'boobies', 'BiggerThanYouThought'])

    return format_output_message(data)

@hook.command(server_id=RODDIT_ID)
def fetish():
    data = get_links_from_subs(['kinky', 'bdsm', 'bondage', 'collared'])

    return format_output_message(data)

@hook.command(server_id=RODDIT_ID)
def teen():
    data = get_links_from_subs(['LegalTeens', 'Just18', 'youngporn', 'barelylegal'])

    return format_output_message(data)

@hook.command(server_id=RODDIT_ID)
def sloboz():
    data = get_links_from_subs(['cumsluts', 'GirlsFinishingTheJob'])

    return format_output_message(data)

@hook.command(server_id=RODDIT_ID)
def anal():
    data = get_links_from_subs(['anal', 'painal'])

    return format_output_message(data)

@hook.command(server_id=RODDIT_ID)
def milf():
    data = get_links_from_subs(['milf'])

    return format_output_message(data)

@hook.command(server_id=RODDIT_ID)
def amateur():
    data = get_links_from_subs(['RealGirls', 'Amateur', 'GoneWild'])

    return format_output_message(data)

@hook.command(server_id=RODDIT_ID)
def traps():
    data = get_links_from_subs(['Tgirls', 'traps', 'gonewildtrans', 'tgifs'])

    return format_output_message(data)

@hook.command(server_id=RODDIT_ID)
def aww():
    data = get_links_from_subs(['aww'])

    return format_output_message(data)

@hook.command(server_id=RODDIT_ID)
def pisi():
    data = get_links_from_subs(['cats'])

    return format_output_message(data)

@hook.command(server_id=RODDIT_ID)
def cutu():
    data = get_links_from_subs(['dogpictures', 'TuckedInPuppies'])

    return format_output_message(data) + " HAM, HAM!"

@hook.command(server_id=RODDIT_ID)
def blep():
    data = get_links_from_subs(['blep', 'blop'])

    return format_output_message(data) + " :P"

@hook.command(server_id=RODDIT_ID)
def capre():
    data = get_links_from_subs(['doggy'])

    return format_output_message(data) + " NSFW!"

@hook.command(server_id=RODDIT_ID)
def lesbiene():
    data = get_links_from_subs(['dykesgonewild'])

    return format_output_message(data) + " NSFW!"

@hook.command(server_id=RODDIT_ID)
def thicc():
    data = get_links_from_subs(['pawg', 'thick'])

    return format_output_message(data) + " NSFW!"

@hook.command(server_id=RODDIT_ID)
def fetch_image(text):
    if text:
        text = text.split()
        data = get_links_from_subs(text)

        return format_output_message(data)
    else:
        return "Please specify a sub or a list of subs (e.g.: .fetch_image RomaniaPorn or .fetch_image RomaniaPorn RoGoneWild)"
