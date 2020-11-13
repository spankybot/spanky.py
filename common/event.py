# For convenience during development, this file is symlinked into each project
from rpc import spanky_pb2

class EventType():
    # Chat events
    message = spanky_pb2.Event.EventType.message
    message_edit = spanky_pb2.Event.EventType.message_edit
    message_del = spanky_pb2.Event.EventType.message_del

    join = spanky_pb2.Event.EventType.join
    part = spanky_pb2.Event.EventType.part

    chan_del = spanky_pb2.Event.EventType.chan_del
    chan_add = spanky_pb2.Event.EventType.chan_add
    chan_upd = spanky_pb2.Event.EventType.chan_upd

    member_ban = spanky_pb2.Event.EventType.member_ban
    member_unban = spanky_pb2.Event.EventType.member_unban
    member_update = spanky_pb2.Event.EventType.member_update

    reaction_add = spanky_pb2.Event.EventType.reaction_add
    reaction_remove = spanky_pb2.Event.EventType.reaction_remove

    msg_bulk_del = spanky_pb2.Event.EventType.msg_bulk_del

    # Bot events
    on_ready = spanky_pb2.Event.EventType.on_ready
    on_start = spanky_pb2.Event.EventType.on_start

    # Non-grpc events
    timer_event = 1000