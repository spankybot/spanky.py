import enum
import logging
import discord

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


'''
class BaseEvent():
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    def prepare(self):
        """
        Initializes this event to be run through it's hook
        """

        if self.hook is None:
            raise ValueError("event.hook is required to prepare an event")

        if "db" in self.hook.required_args:
            logger.debug("Opening database session for {}:threaded=True".format(self.hook.description))

            self.db = self.db.db_session()

    def close(self):
        """
        Closes this event after running it through it's hook.

        Mainly, closes the database connection attached to this event (if any).

        This method is for when the hook is *not* threaded (event.hook.threaded is False).
        If you need to add a db to a threaded hook, use close_threaded.
        """
        if self.hook is None:
            raise ValueError("event.hook is required to close an event")

        if "db" in self.hook.required_args:
            #logger.debug("Closing database session for {}:threaded=False".format(self.hook.description))
            # be sure the close the database in the database executor, as it is only accessable in that one thread
            self.db.close()
            self.db = None

    def reply(self, text, allowed_mentions=discord.AllowedMentions(everyone=False, users=True, roles=True)):
        self.event.reply(text, allowed_mentions=allowed_mentions)

class TextEvent(BaseEvent):
    def __init__(self, hook, text, triggered_command, event, bot, permission_mgr):
        super().__init__(bot)
        self.hook = hook
        self.text = text
        self.triggered_command = triggered_command
        self.event = event
        self.permission_mgr = permission_mgr

        self.doc = self.hook.doc

    def notice_doc(self, target=None):
        """sends a notice containing this command's docstring to the current channel/user or a specific channel/user
        :type target: str
        """
        self.notice("unimplemented docstring", target=target)

class OnStartEvent(BaseEvent):
    def __init__(self, bot, hook):
        super().__init__(bot)
        self.hook = hook

class OnReadyEvent(BaseEvent):
    def __init__(self, bot, hook, permission_mgr, server):
        super().__init__(bot)
        self.hook = hook
        self.permission_mgr = permission_mgr
        self.server = server
        self.event = None

class OnConnReadyEvent(BaseEvent):
    def __init__(self, bot, hook):
        super().__init__(bot)
        self.hook = hook
        self.event = None

class TimeEvent(BaseEvent):
    def __init__(self, bot, hook, event):
        super().__init__(bot)
        self.hook = hook
        self.event = event

class HookEvent(BaseEvent):
    def __init__(self, bot, hook, event, permission_mgr):
        super().__init__(bot)
        self.hook = hook
        self.event = event
        self.permission_mgr = permission_mgr

'''
