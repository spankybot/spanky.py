import re
import os
import codecs
import time
import psycopg2

from datetime import datetime
from spanky.plugin import hook
from spanky.plugin.event import EventType
from spanky.plugin.permissions import Permission

base_formats = {
    EventType.message: "{msg_id}: [{hour}:{minute}:{second}] <{nick}> {content}",
}

db_conn = None


@hook.on_start()
def init_db(bot):
    global db_conn

    db_host = bot.config.get("db_host", None)
    db_name = bot.config.get("db_name", None)
    db_user = bot.config.get("db_user", None)
    db_pass = bot.config.get("db_pass", None)

    try:
        if db_name != None and db_user != None:
            db_conn = psycopg2.connect(
                "host=%s dbname=%s user=%s password=%s" % (db_host, db_name, db_user, db_pass))
    except:
        import traceback
        traceback.print_exc()


def get_format_args(event):
    # Setup arguments
    hour, minute, second = time.strftime("%H,%M,%S").split(',')

    # Handle PMs
    server_name = "pm"
    server_id = "0"
    channel_name = "pm"
    channel_id = "0"
    if hasattr(event, "server"):
        server = event.server.name
        server_id = event.server.id
        channel_name = event.channel.name
        channel_id = event.channel.id

    args = {
        "msg_id": event.msg.id,
        "server": server_name,
        "server_id": server_id,
        "channel": channel_name,
        "channel_id": channel_id,
        "nick": event.author.name + "/" + event.author.nick + "/" + str(event.author.id),
        "author": event.author.name,
        "author_id": event.author.id,
        "hour": hour,
        "minute": minute,
        "second": second,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    if event.text is not None:
        args["content"] = event.text
    else:
        args["content"] = ""

    return args


def format_event(event, args):
    return base_formats[event.type].format(**args)

# +--------------+
# | File logging |
# +--------------+


file_format = "{channel}_%Y%m%d.log"
folder_format = "logs/{server_id}/%Y/"

# Stream cache, (server, chan) -> (file_name, stream)
stream_cache = {}


def get_log_filename(event, args):
    current_time = time.localtime()
    folder_name = time.strftime(folder_format, current_time)
    file_name = time.strftime(file_format, current_time).lower()

    folder_name = folder_name.format(**args)
    file_name = file_name.format(**args)

    return os.path.join("logs", folder_name, file_name)


def get_log_stream(event, args):
    new_filename = get_log_filename(event, args)

    # Handle PMs
    channel_id = "pm"
    server_id = "0"
    if hasattr(event, "server"):
        channel_id = event.channel.id
        server_id = event.server.id

    cache_key = (server_id, channel_id)
    old_filename, log_stream = stream_cache.get(cache_key, (None, None))

    # If the filename has changed since we opened the stream, we should re-open
    if new_filename != old_filename:
        # If we had a stream open before, we should close it
        if log_stream is not None:
            log_stream.flush()
            log_stream.close()

        logging_dir = os.path.dirname(new_filename)
        os.makedirs(logging_dir, exist_ok=True)

        # a dumb hack to bypass the fact windows does not allow * in file names
        new_filename = new_filename.replace("*", "server")

        log_stream = codecs.open(
            new_filename, mode="a", encoding="utf-8", buffering=1)
        stream_cache[cache_key] = (new_filename, log_stream)

    return log_stream


@hook.event(EventType.message)
def log(bot, event):
    args = get_format_args(event)

    file_log(event, args)
    console_log(bot, event, args)

    try:
        db_log(event, args)
    except psycopg2.InternalError as e:
        print(e)
        init_db(bot)


def file_log(event, args):
    text = format_event(event, args)

    if text is not None:
        stream = get_log_stream(event, args)
        stream.write(text + os.linesep)
        stream.flush()


def console_log(bot, event, args):
    text = format_event(event, args)

    if text is not None:
        bot.logger.info(text)


def db_log(event, args):
    if not db_conn:
        return

    cs = db_conn.cursor()
    cs.execute("""insert into messages (id, date, author, author_id, msg, channel, channel_id, server, server_id) \
            values(%s, %s, %s, %s, %s, %s, %s, %s, %s);""", (
        args["msg_id"],
        args["timestamp"],
        args["author"],
        args["author_id"],
        args["content"],
        args["channel"],
        args["channel_id"],
        args["server"],
        args["server_id"]))
    db_conn.commit()


def log_msg(msg):
    args = {}
    args["msg_id"] = msg.id
    args["timestamp"] = msg.timestamp
    args["author"] = msg.author.name
    args["author_id"] = msg.author.id
    args["content"] = msg.content
    args["channel"] = msg.channel.name
    args["channel_id"] = msg.channel.id
    args["server"] = msg.server.name
    args["server_id"] = msg.server.id

    cs = db_conn.cursor()
    cs.execute("""select * from messages where id = %s;""", (args["msg_id"],))
    out = cs.fetchall()
    if len(out) == 0:
        cs.execute("""insert into messages (id, date, author, author_id, msg, channel, channel_id, server, server_id) \
            values(%s, %s, %s, %s, %s, %s, %s, %s, %s);""", (
            args["msg_id"],
            args["timestamp"],
            args["author"],
            args["author_id"],
            args["content"],
            args["channel"],
            args["channel_id"],
            args["server"],
            args["server_id"]))
        db_conn.commit()


@hook.command()
def seen_user(text, str_to_id):
    """
    Get the last time when a user was seen saying something on a server where the bot is also present
    """
    uid = str_to_id(text)

    cs = db_conn.cursor()

    try:
        cs.execute(
            """select * from messages where author_id=%s order by date desc limit 1""", (str(uid),))
    except:
        db_conn.rollback()
        return "Invalid input"

    data = cs.fetchall()
    _, seen, _, _, _, _, _, _, _ = data[0]

    return "Last seen on: %s UTC" % (str(seen))


def get_msg_cnt_for_user(uid):
    cs = db_conn.cursor()
    cs.execute("""select count(*) from messages where author_id=%s""", (str(uid),))

    return cs.fetchall()[0][0]


def get_msg_cnt_for_channel(cid):
    cs = db_conn.cursor()
    cs.execute(
        """select count(*) from messages where channel_id=%s""", (str(cid),))

    return cs.fetchall()[0][0]


def get_msg_cnt_for_channel_after(cid, lower):
    cs = db_conn.cursor()

    cs.execute("""select count(*) from messages where channel_id=%s and date>%s""",
               (str(cid), str(datetime.fromtimestamp(lower)),))

    return cs.fetchall()[0][0]


def get_msgs_for_user_in_chan(uid, cid, limit):
    cs = db_conn.cursor()
    try:
        cs.execute("""select msg from messages where author_id=%s and channel_id=%s order by date desc limit %s""",
                   (str(uid), str(cid), str(limit)))
    except:
        import traceback
        traceback.print_exc()
        db_conn.rollback()
        print("Error getting messages for %s in %s" % (uid, cid))
        return []

    data = cs.fetchall()

    return [i[0] for i in data]


def get_msgs_in_chan(cid, limit):
    cs = db_conn.cursor()
    try:
        cs.execute("""select msg from messages where channel_id=%s order by date desc limit %s""",
                   (str(cid), str(limit)))
    except:
        import traceback
        traceback.print_exc()
        db_conn.rollback()
        print("Error getting messages for %s in %s" % (uid, cid))
        return []

    data = cs.fetchall()

    return [i[0] for i in data]


async def rip_channel(client, ch):
    before = None
    old_bef = None
    while True:
        print("Current timestamp " + str(before))
        async for i in client.logs_from(ch, limit=1000, reverse=True, before=before):
            log_msg(i)
            before = i.timestamp

        time.sleep(0.5)
        if old_bef == before:
            break
        else:
            old_bef = before


@hook.command(permissions=Permission.bot_owner)
async def ripmusic(event, reply):
    link = re.compile(
        r"(https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|www\.[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9]+\.[^\s]{2,}|www\.[a-zA-Z0-9]+\.[^\s]{2,})")

    out = open("music.csv", "w")
    total = 0
    async for i in event.channel._raw.history(limit=None):
        finds = re.findall(link, i.content)
        print(i.content)

        for finding in finds:
            data = "%s, %s, %s\n" % (
                i.author.name, i.created_at, "".join(finding))
            out.write(data)

            total += 1

        if total % 100 == 0 and total != 0:
            reply("Found %d links" % total)


@hook.command(permissions=Permission.bot_owner)
async def rip_servers(bot):
    import discord
    client = bot.backend.client

    gen = client.get_all_channels()

    for ch in gen:
        if ch.type == discord.ChannelType.text:
            print("Ripping " + str(ch))
            try:
                await rip_channel(client, ch)
            except:
                import traceback
                traceback.print_exc()


@hook.command(permissions=Permission.bot_owner)
def cntusr(text):
    return get_msg_cnt_for_user(text)


@hook.command()
def asdasdasda(server):
    for user in server.get_users():
        print(user.name)
