import os
import codecs
import time

from spanky.plugin import hook
from spanky.plugin.event import EventType

base_formats = {
    EventType.message: "{msg_id}: [{hour}:{minute}:{second}] <{nick}> {content}",
}

def get_format_args(event):
    # Setup arguments
    hour, minute, second = time.strftime("%H,%M,%S").split(',')

    args = {
        "msg_id": event.msg.id,
        "server": event.server.name, 
        "server_id": event.server.id,
        "channel": event.channel.name, 
        "nick": event.author.name + "/" + event.author.nick + "/" + event.author.id,
        "hour": hour,
        "minute": minute,
        "second": second
    }

    if event.text is not None:
        args["content"] = event.text
    else:
        args["content"] = None

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
    cache_key = (event.server.id, event.channel.id)
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

        log_stream = codecs.open(new_filename, mode="a", encoding="utf-8", buffering=1)
        stream_cache[cache_key] = (new_filename, log_stream)

    return log_stream

@hook.event(EventType.message)
def log(event):
    args = get_format_args(event)
    text = format_event(event, args)

    if text is not None:
        stream = get_log_stream(event, args)
        stream.write(text + os.linesep)
        stream.flush()


@hook.event(EventType.message)
def console_log(bot, event):
    args = get_format_args(event)
    text = format_event(event, args)
    
    if text is not None:
        bot.logger.info(text)
