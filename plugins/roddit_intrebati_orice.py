import praw
import time
from spanky.plugin import hook
from datetime import datetime

USER_AGENT = ""
LAST_CHECK = 0
RODDIT_ID = "297483005763780613"

stor = None
roddit = None

@hook.command(server_id=RODDIT_ID)
def set_updates_channel(text, str_to_id):
    """
    <channel> - Send 'intrebati orice' on channel.
    """
    stor['channel'] = str_to_id(text)
    return "Done."

@hook.command(server_id=RODDIT_ID)
def clear_updates_channel():
    """
    Remove 'intrebati orice' announcement channel.
    """
    stor['channel'] = None
    return "Done."

@hook.command(server_id=RODDIT_ID)
def get_updates_channel(id_to_chan):
    """
    List 'intrebati orice' annoucement channel.
    """
    if stor['channel']:
        return id_to_chan(stor['channel'])
    else:
        return "Not set."

@hook.on_ready()
def init(server, storage):
    global USER_AGENT
    global LAST_CHECK

    USER_AGENT = "/r/Romania scraper by /u/programatorulupeste"
    LAST_CHECK = (datetime.utcnow() - datetime(1970, 1, 1)).total_seconds()
    
    if server.id == RODDIT_ID:
        global stor
        global roddit
        stor = storage
        roddit = server

def split_list(text, max_len):
    ret = []
    start = 0
    crt = start

    text = text.replace('\n', ' ')

    if len(text) > max_len:
        while crt + max_len < len(text):
            crt_max_len = max_len
            while crt_max_len > 1 and text[crt + crt_max_len] != ' ':
                    crt_max_len -= 1
            if crt_max_len == 1:
                crt_max_len = max_len
            ret.append(text[crt:crt + crt_max_len])
            crt += crt_max_len

    ret.append(text[crt:crt + max_len])
    return ret

def wrap_message(comm):
    msg = "**Intrebare noua** de la %s: %s -> <%s>" % (comm.author.name, comm.body, (comm.submission.shortlink).replace("http://redd.it", "http://ssl.reddit.com"))
    return split_list(msg, 400)

@hook.periodic(10, initial_interval = 10)
def checker(send_message):
    global USER_AGENT
    global LAST_CHECK
    
    try:
        r = praw.Reddit("irc_bot", user_agent=USER_AGENT)
        subreddit = r.subreddit('romania')

        submission = subreddit.hot(limit = 2)

        for x in submission:
            if x.stickied == True and "/r/Romania Orice" in x.title:
                for c in reversed(x.comments):
                    if hasattr(c, 'created_utc') and  c.created_utc > LAST_CHECK:
                        LAST_CHECK = c.created_utc

                        msg = list(wrap_message(c))
                        for i in msg:
                            send_message(target=stor['channel'], text=i, server=roddit)
                        return
    except BaseException as e:
        print(str(e))
