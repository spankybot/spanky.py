import enum
import logging
import concurrent.futures

logger = logging.getLogger("spanky")

@enum.unique
class EventType(enum.Enum):
    message         = 0
    message_edit    = 1
    message_del     = 2
    join            = 3
    part            = 4
    chan_del        = 5
    chan_add        = 6
    chan_upd        = 7

    other           = 99
    action          = 100

class Event:
    def __init__(self, bot=None, hook=None, base_event=None):

        self.db = None
        self.db_executor = None
        self.bot = bot
        self.hook_type = hook
        self.server = None

    @property
    def hook(self):
        return self.hook_type

    def prepare(self):
        """
        Initializes this event to be run through it's hook

        Mainly, initializes a database object on this event, if the hook requires it.

        This method is for when the hook is *not* threaded (event.hook.threaded is False).
        If you need to add a db to a threaded hook, use prepare_threaded.
        """

        if self.hook is None:
            raise ValueError("event.hook is required to prepare an event")

        if "db" in self.hook.required_args:
            logger.debug("Opening database session for {}:threaded=False".format(self.hook.description))

            # we're running a coroutine hook with a db, so initialise an executor pool
            self.db_executor = concurrent.futures.ThreadPoolExecutor(1)
            # be sure to initialize the db in the database executor, so it will be accessible in that thread.
            self.db = self.bot.db_session

    def prepare_threaded(self):
        """
        Initializes this event to be run through it's hook

        Mainly, initializes the database object on this event, if the hook requires it.

        This method is for when the hook is threaded (event.hook.threaded is True).
        If you need to add a db to a coroutine hook, use prepare.
        """

        if self.hook is None:
            raise ValueError("event.hook is required to prepare an event")

        if "db" in self.hook.required_args:
            logger.debug("Opening database session for {}:threaded=True".format(self.hook.description))

            self.db = self.bot.db_session()

    def close(self):
        """
        Closes this event after running it through it's hook.

        Mainly, closes the database connection attached to this event (if any).

        This method is for when the hook is *not* threaded (event.hook.threaded is False).
        If you need to add a db to a threaded hook, use close_threaded.
        """
        if self.hook is None:
            raise ValueError("event.hook is required to close an event")

        if self.db is not None:
            #logger.debug("Closing database session for {}:threaded=False".format(self.hook.description))
            # be sure the close the database in the database executor, as it is only accessable in that one thread
            yield from self.async(self.db.close)
            self.db = None

    def close_threaded(self):
        """
        Closes this event after running it through it's hook.

        Mainly, closes the database connection attached to this event (if any).

        This method is for when the hook is threaded (event.hook.threaded is True).
        If you need to add a db to a coroutine hook, use close.
        """
        if self.hook is None:
            raise ValueError("event.hook is required to close an event")
        if self.db is not None:
            #logger.debug("Closing database session for {}:threaded=True".format(self.hook.description))
            self.db.close()
            self.db = None

    @property
    def event(self):
        """
        :rtype: Event
        """
        return self

    @property
    def loop(self):
        """
        :rtype: asyncio.events.AbstractEventLoop
        """
        return self.bot.loop

    @property
    def logger(self):
        return logger

    def message(self, message, target=None):
        """sends a message to a specific or current channel/user
        :type message: str
        :type target: str
        """
        if target is None:
            if self.chan is None:
                raise ValueError("Target must be specified when chan is not assigned")
            target = self.chan
        self.conn.message( target, message)

    def reply(self, *messages, target=None):
        """sends a message to the current channel/user with a prefix
        :type message: str
        :type target: str
        """

        if not messages:  # if there are no messages specified, don't do anything
            return

#        if target == self.nick or not reply_ping:
#            self.conn.message(target, *messages)
#        else:
        self.conn.message(self.chan, "({}) {}".format(self.nick, messages[0]), *messages[1:])

    def action(self, message, target=None):
        """sends an action to the current channel/user or a specific channel/user
        :type message: str
        :type target: str
        """
        if target is None:
            if self.chan is None:
                raise ValueError("Target must be specified when chan is not assigned")
            target = self.chan

        self.conn.action(self.chan, message)

    def notice(self, message, target=None):
        """sends a notice to the current channel/user or a specific channel/user
        :type message: str
        :type target: str
        """
        avoid_notices = self.conn.config.get("avoid_notices", False)
        if target is None:
            if self.nick is None:
                raise ValueError("Target must be specified when nick is not assigned")
            target = self.nick

        # we have a config option to avoid noticing user and PM them instead, so we use it here
        #if avoid_notices:
        #self.conn.message(target, message)
        self.conn.message(self.chan, message)
        #else:
        #    self.conn.notice(target, message)

    def has_permission(self, permission, notice=True):
        """ returns whether or not the current user has a given permission
        :type permission: str
        :rtype: bool
        """
        if not self.mask:
            raise ValueError("has_permission requires mask is not assigned")
        return self.conn.permissions.has_perm_mask(self.mask, permission, notice=notice)

    def check_permission(self, permission, notice=True):
        """ returns whether or not the current user has a given permission
        :type permission: str
        :type notice: bool
        :rtype: bool
        """
        if self.has_permission(permission, notice=notice):
            return True

        for perm_hook in self.bot.plugin_manager.perm_hooks[permission]:
            # noinspection PyTupleAssignmentBalance
            ok, res = yield from self.bot.plugin_manager.internal_launch(perm_hook, self)
            if ok and res:
                return True

        return False

    def check_permissions(self, *perms, notice=True):
        for perm in perms:
            if (yield from self.check_permission(perm, notice=notice)):
                return True

        return False

class BaseEvent():
    def __init__(self, bot):
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

class TextEvent(BaseEvent):
    def __init__(self, hook, text, triggered_command, event, bot=None):
        """
        :param text: The arguments for the command
        :param triggered_command: The command that was triggered
        :type text: str
        :type triggered_command: str
        """
        super().__init__(bot)
        self.hook = hook
        self.text = text
        self.triggered_command = triggered_command
        self.event = event
        
        self.doc = self.hook.doc

    def notice_doc(self, target=None):
        """sends a notice containing this command's docstring to the current channel/user or a specific channel/user
        :type target: str
        """
        self.notice("unimplemented docstring", target=target)

class TimeEvent(BaseEvent):
    def __init__(self, hook, bot=None):
        """
        :param text: The arguments for the command
        :param triggered_command: The command that was triggered
        :type text: str
        :type triggered_command: str
        """
        super().__init__(bot)
        self.hook = hook

class RegexEvent(Event):
    """
    :type hook: cloudbot.plugin.RegexHook
    :type match: re.__Match
    """

    def __init__(self, *, bot=None, hook, match, conn=None, base_event=None, event_type=None, content=None, target=None,
                 channel=None, nick=None, user=None, host=None, mask=None, msg_raw=None, irc_prefix=None,
                 irc_command=None, irc_paramlist=None):
        """
        :param: match: The match objected returned by the regex search method
        :type match: re.__Match
        """
        super().__init__(bot=bot, conn=conn, hook=hook, base_event=base_event, event_type=event_type, content=content,
                         target=target, channel=channel, nick=nick, user=user, host=host, mask=mask, msg_raw=msg_raw,
                         irc_prefix=irc_prefix, irc_command=irc_command, irc_paramlist=irc_paramlist)
        self.match = match
