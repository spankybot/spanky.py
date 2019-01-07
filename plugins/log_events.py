from spanky.plugin import hook
from spanky.plugin.event import EventType
from spanky.plugin.permissions import Permission

@hook.on_ready
def log_prepare(storage):
    if "chan_filter_list" not in storage.keys():
        storage["chan_filter_list"] = []
    
    if "evt_chan" not in storage.keys():
        storage["evt_chan"] = None

@hook.command(permissions=Permission.admin, format="chan")
def set_event_log_chan(text, storage, str_to_id):
    """
    <channel> - Activate event logging and log to channel.
Logged events: user join, user leave, message edit, message delete, member update, member ban, member unban.
    """
    storage["evt_chan"] = str_to_id(text)
    return "Done."

@hook.command(permissions=Permission.admin)
def clear_event_log_chan(storage):
    """
    <channel> - Clear logging channel and deactivate logging.
    """
    storage["evt_chan"] = None
    return "Done."

@hook.command(permissions=Permission.admin)
def get_event_log_chan(storage, id_to_chan):
    """
    <channel> - Get the event log channel.
    """
    if storage["evt_chan"]:
        return id_to_chan(storage["evt_chan"])
    
    return "Not set."

@hook.command(permissions=Permission.admin, format="channel")
def add_filter_out_channel(text, str_to_id, storage):
    """
    <channel> - Don't log events on a certain channel.
    """
    chan_list = storage["chan_filter_list"]
    if not chan_list:
        chan_list = []
        
    chan_list.append(str_to_id(text))
        
    storage["chan_filter_list"] = chan_list
    
    return "Done."

@hook.command(permissions=Permission.admin, format="channel")
def clear_filter_out_channel(text, str_to_id, storage):
    """
    <channel> - Remove channel event filtering.
    """
    chan_id = str_to_id(text)
    chan_list = storage["chan_filter_list"]
    if not chan_list:
        chan_list = []
    
    if chan_id not in chan_list:
        return
    
    chan_list.remove(chan_id)
    storage["chan_filter_list"] = chan_list
    
    return "Done."

@hook.command(permissions=Permission.admin)
def list_filtered_out_channels(id_to_chan, storage):
    """
    <channel> - List filtered channels.
    """
    chan_list = storage["chan_filter_list"]
    
    if chan_list and len(chan_list) > 0:
        return ", ".join(id_to_chan(chan) for chan in chan_list)
    else:
        return "Not set."

def escape(msg):
    msg = msg.replace("<@", "<\@")
    msg = msg.replace("`", "\`")
    return msg

@hook.event(EventType.join)
def log_join(event, storage, send_message):
    send_message(storage["evt_chan"],
        "⚠`Join: ` %s %s" % (event.author.name, event.author.id))

@hook.event(EventType.part)
def log_part(event, storage, send_message):
    send_message(storage["evt_chan"],
        "🔚`Part: ` %s %s" % (event.author.name, event.author.id))


@hook.event(EventType.message_edit)
def log_message_edit(event, send_message, storage):
    if event.before.channel.id in storage["chan_filter_list"]:
        return

    if event.before.text == event.after.text:
        return

    send_message(
        "`Edited` %s `->` %s `in` %s `ID:` %s `by` %s" % (
        escape(event.before.text),
        escape(event.after.text),
        event.before.channel.name,
        event.after.msg.id,
        event.after.author.name
        ), 
        storage["evt_chan"])

@hook.event(EventType.message_del)
def log_message_del(event, send_message, storage):
    if event.channel.id in storage["chan_filter_list"]:
        return

    send_message(target=storage["evt_chan"],
        text="`Deleted` %s `in` %s `ID: ` %s `by` %s" %
        (escape(event.msg.text),
        event.channel.name,
        event.msg.id,
        event.author.name
        ))

@hook.event(EventType.member_update)
def log_member_update(event, send_message, storage):
    if set(event.before.member.roles) != set(event.after.member.roles):
        send_message(target=storage["evt_chan"],
            text="`Member update` %s: `before` %s, `after` %s" %
            (event.before.member.nick,
                ", ".join(i.name for i in event.before.member.roles),
                ", ".join(i.name for i in event.after.member.roles)))

    if event.before.member.nick != event.after.member.nick:
        send_message(target=storage["evt_chan"],
            text="`Nick change` `before` %s, `after` %s" %
                (event.before.member.nick, event.after.member.nick))

@hook.event(EventType.member_ban)
def log_member_ban(event, send_message, storage):
    send_message(target=storage["evt_chan"], 
         text="`Banned`: %s %s" % (event.member.name, event.member.id))

@hook.event(EventType.member_unban)
def log_member_unban(event, send_message, storage):
    send_message(target=storage["evt_chan"], 
         text="`Unban`: %s %s" % (event.user.name, event.user.id))
