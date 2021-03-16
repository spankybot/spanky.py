import praw
import time
from spanky.plugin import hook
from spanky.plugin.permissions import Permission

tstamps = {}
reddit_inst = None
g_db = None

storages = {}
servers = {}


def set_crt_timestamps():
    global tstamps

    epoch = int(time.time())

    for _, storage in storages.items():
        if not storage["subs"]:
            storage["subs"] = {}

        for sub in storage["subs"].keys():
            storage["subs"][sub]["timestamp"] = epoch
        storage.sync()


@hook.on_start()
def init():
    global reddit_inst
    reddit_inst = praw.Reddit(
        "irc_bot", user_agent='Subreddit watcher by /u/programatorulupeste')


@hook.on_ready()
def ready(server, storage):
    storages[server.id] = storage
    servers[server.id] = server

    # Set the current time for each subreddit
    set_crt_timestamps()


def do_it(thread):
    sub = thread.subreddit.display_name
    prefix = '**Self post:**' if thread.is_self else '**Link post:**'
    message = '"%s" posted in /r/%s by %s. <%s>' % (
        thread.title,
        sub,
        thread.author,
        (thread.shortlink).replace("http://redd.it", "http://ssl.reddit.com")
    )

    return prefix + " " + message


@hook.periodic(30)
def checker(send_message):
    global reddit_inst

    for server_id, storage in storages.items():
        if storage["watching"] == False:
            continue

        for sub in storage["subs"].keys():
            try:
                subreddit = reddit_inst.subreddit(sub)
                newest = storage["subs"][sub]["timestamp"]

                for submission in subreddit.new():
                    subtime = submission.created_utc
                    if subtime > storage["subs"][sub]["timestamp"]:
                        if subtime > newest:
                            newest = subtime
                            storage["subs"][sub]["timestamp"] = newest
                            storage.sync
                        send_message(target=storage["channel"], text=do_it(
                            submission), server=servers[server_id])

            except BaseException as e:
                print(str(e))
                print("Exception generated for sub: " + sub)


@hook.command
def subwatch_list(event):
    """
    List watched subreddits.
    """
    if storages[event.server.id]["subs"]:
        return 'Watching: ' + ", ".join(i for i in storages[event.server.id]["subs"])
    else:
        return "Empty."


@hook.command(permissions=Permission.admin, format="sub")
def subwatch_add(text, event):
    """
    Add a subreddit to the watch list.
    """
    if storages[event.server.id]["subs"] == None:
        storages[event.server.id]["subs"] = {}

    storages[event.server.id]["subs"][text] = {}
    storages[event.server.id]["subs"][text]["timestamp"] = int(time.time())
    storages[event.server.id].sync()
    return "Done"


@hook.command(permissions=Permission.admin)
def subwatch_del(text, event):
    """
    Remove a subreddit from the watch list
    """
    if storages[event.server.id]["subs"] == None:
        return "Storage empty"
    else:
        del storages[event.server.id]["subs"][text]
        storages[event.server.id].sync()
        return "OK."


@hook.command(permissions=Permission.admin)
def startwatch(event):
    """
    Start watching subreddits.
    """
    storages[event.server.id]["watching"] = True
    set_crt_timestamps()
    return "Started watching"


@hook.command(permissions=Permission.admin)
def stopwatch(event):
    """
    Stop watching subreddits.
    """
    storages[event.server.id]["watching"] = False
    return "Stopped watching"


@hook.command(permissions=Permission.admin, format="chan")
def set_rupdates_channel(text, str_to_id, event):
    """
    <channel> - Send reddit updates on channel.
    """
    storages[event.server.id]['channel'] = str_to_id(text)
    return "Done."


@hook.command(permissions=Permission.admin)
def clear_rupdates_channel(event):
    """
    Remove reddit updates channel.
    """
    storages[event.server.id]['channel'] = None
    return "Done."


@hook.command(permissions=Permission.admin)
def get_rupdates_channel(id_to_chan, event):
    """
    List reddit updates annoucement channel.
    """
    if storages[event.server.id]['channel']:
        return id_to_chan(storages[event.server.id]['channel'])
    else:
        return "Not set."
