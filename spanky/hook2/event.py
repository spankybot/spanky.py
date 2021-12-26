import enum
import logging

logger = logging.getLogger("spanky")


@enum.unique
class EventType(enum.Enum):
    # Discord events
    message = 0
    message_edit = 1
    message_del = 2
    join = 3
    part = 4
    chan_del = 5
    chan_add = 6
    chan_upd = 7

    member_ban = 8
    member_unban = 9
    member_update = 10

    reaction_add = 11
    reaction_remove = 12

    msg_bulk_del = 13

    # Bot events
    command = 100
    periodic = 101
    on_start = 102
    on_ready = 103
    on_conn_ready = 104
