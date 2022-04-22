# Delay checking for typing (TODO: remove when bot runs on python 3.10)
from __future__ import annotations
from collections import deque

from spanky.hook2 import storage
from spanky.hook2.complex_cmd import ComplexCommand
from .hooklet import (
    Command,
    MessageReact,
    Periodic,
    Event,
    Middleware,
    MiddlewareType,
    MiddlewareResult,
)
import asyncio
import random
from typing import Any, Callable, Optional, TYPE_CHECKING
from .event import EventType
from .actions import ActionPeriodic

if TYPE_CHECKING:
    from .actions import (
        Action,
        ActionCommand,
        ActionEvent,
    )
    from hooklet import Hooklet

    MiddlewareFunc = Callable[[Action, Hooklet], Optional[MiddlewareResult]]

# copy-paste from old plugin manager
import logging

logger = logging.getLogger("spanky")
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)


class Hook:
    hash = random.randint(0, 2**31)

    def __init__(
        self,
        hook_id: str,
        *,
        storage_name: str = "",
        parent_hook: Optional[Hook] = None,
        handler_queue_limit: int = 50,
    ):
        self.hook_id: str = hook_id

        # Hooklet dicts
        self.commands: dict[str, Command] = {}
        self.periodics: dict[str, Periodic] = {}
        self.events: dict[str, Event] = {}
        self.global_md: dict[str, Middleware] = {}
        self.local_md: dict[str, Middleware] = {}

        # Storage object
        self.storage_name = hook_id
        if storage_name != "":
            self.storage_name = storage_name

        # Tree
        self.parent_hook: Optional[Hook] = parent_hook
        if self.parent_hook != None and not self.parent_hook.has_child(self):
            self.parent_hook.add_child(self)

        self.children: list[Hook] = []

        # Message event handler subcomponent
        self.rolling_handlers: deque[MessageReact] = deque(maxlen=handler_queue_limit)
        self.permanent_handlers: list[MessageReact] = []

    # def __del__(self):
    #    self.unload()

    # unload unloads the entire subtree
    def unload(self):
        if self.parent_hook:
            self.parent_hook.remove_child(self.hook_id)
        for child in self.children:
            child.unload()

    def __str__(self):
        return f"Hook[{self.hook_id=}{f', parent: {self.parent_hook.hook_id}' if self.parent_hook else ''}]"

    def __repr__(self):
        return self.__str__()

    def __hash__(self):
        return self.hash

    def __eq__(self, other):
        if isinstance(other, Hook):
            return self.hook_id == other.hook_id
        if isinstance(other, str):
            return self.hook_id == other
        return False

    # add_child adds a new child hook to the tree, directly underneath the current Hook. It throws a TypeError if the child hook is already in the tree
    def add_child(self, child: Hook):
        if not self.root.has_child(child):
            self.children.append(child)
            child.parent_hook = self
        else:
            raise TypeError("Hook already in tree.")

    # TODO FOR ALL OF THESE PROPERTIES: CACHE AND INVALIDATION

    @property
    def root(self) -> Hook:
        root_hook: Hook = self
        while root_hook.parent_hook:
            root_hook = root_hook.parent_hook
        return root_hook

    @property
    def all_commands(self) -> dict[str, Command]:
        commands = self.commands.copy()
        for child in self.children:
            commands |= child.all_commands
        return commands

    def remove_command(self, name: str) -> bool:
        cmd = self.get_local_command(name)
        if cmd == None:
            return False
        self.commands.pop(cmd.name)
        return True

    def get_command(self, name: str) -> Optional[Command]:
        for cmd in self.all_commands.values():
            if cmd.name == name or name in cmd.aliases:
                return cmd
        return None

    def get_local_command(self, name: str) -> Command:
        for cmd in self.commands.values():
            if cmd.name == name or name in cmd.aliases:
                return cmd
        return None

    @property
    def all_periodics(self) -> dict[str, Periodic]:
        periodics = self.periodics.copy()
        for child in self.children:
            periodics |= child.all_periodics
        return periodics

    @property
    def all_global_middleware(self) -> dict[str, Middleware]:
        global_md = self.global_md.copy()
        for child in self.children:
            global_md |= child.all_global_middleware
        return global_md

    @property
    def all_local_middleware(self) -> dict[str, Middleware]:
        local_md = {}
        root_hook = self
        while root_hook.parent_hook:
            local_md |= root_hook.local_md
            root_hook = root_hook.parent_hook
        return local_md

    # self.all_middleware is shorthand for a sorted self.all_global_middleware | self.all_local_middleware
    @property
    def all_middleware(self) -> dict[str, Middleware]:
        return dict(
            sorted(
                (self.root.all_global_middleware | self.all_local_middleware).items(),
                key=lambda item: item[1].priority,
            )
        )

    async def run_middleware(self, act: ActionCommand, hooklet: Command):
        # copy action to avoid multiple usages
        action = act.copy()

        mds = self.all_middleware
        # print(mds.keys())
        for md in mds.values():
            rez, msg = await md.handle(action, hooklet)
            if rez == MiddlewareResult.DENY and len(msg) > 1:
                action.reply(msg, timeout=15)
                return
        # Run middleware for the subcommand
        if isinstance(hooklet, ComplexCommand):
            cmd, action = hooklet.get_cmd(action)

            await self.run_middleware(action, cmd)
        else:
            await hooklet.handle(action)

    # has_child walks down the tree and says if the node has the specified hook as a descendant
    def has_child(self, hook: Hook) -> bool:
        if self == hook:
            return True
        for child in self.children:
            if child == hook:
                return True
            if child.has_child(hook):
                return True
        return False

    def find_hook(self, hook_id: str) -> Optional[Hook]:
        if self.hook_id == hook_id:
            return self
        for child in self.children:
            hk = child.find_hook(hook_id)
            if hk != None:
                return hk
        return None

    # remove_child removes a child hook if it is directly underneath the current node.
    def remove_child(self, hook_id: str):
        try:
            self.children = [
                child for child in self.children if child.hook_id != hook_id
            ]
        except Exception as e:
            print(e)
            pass

    # Event propagation
    # The return of this function marks the finalization of propagating across the entire subtree
    async def dispatch_action(self, action: Action):
        # if self.hook_id == "bot_hook" and not isinstance(action, ActionPeriodic):
        #    print(self.hook_id, action)

        tasks = []

        if action.event_type is EventType.command:
            # Command trigger
            action: ActionCommand = action
            hooklet = self.get_local_command(action.triggered_command)
            if hooklet:
                # Do with middleware
                tasks.append(
                    asyncio.create_task(self.run_middleware(action, hooklet), name="")
                )
        elif action.event_type is EventType.periodic:
            # Periodic trigger
            action: ActionPeriodic = action
            for periodic in self.periodics.values():
                if periodic.hooklet_id == action.target:
                    tasks.append(asyncio.create_task(periodic.handle(action)))
        elif action.event_type is EventType.reaction_add and action.msg != None:
            action: ActionEvent = action
            for handler in self.permanent_handlers:
                if handler.msg_id == action.msg.id:
                    tasks.append(asyncio.create_task(handler.handle(action)))
            for handler in self.rolling_handlers:
                if handler.msg_id == action.msg.id:
                    tasks.append(asyncio.create_task(handler.handle(action)))

        # Gobble all matching event coroutines
        # If it's a message in a PM, don't register the event (compatibility with hook1)
        if not (
            action.is_pm
            and action.event_type
            in [EventType.message, EventType.message_del, EventType.message_edit]
        ):
            for event_hooklet in self.events.values():
                if action.event_type in event_hooklet.event_types:
                    tasks.append(asyncio.create_task(event_hooklet.handle(action)))

        # Gobble children dispatch coroutines
        for child in self.children:
            tasks.append(asyncio.create_task(child.dispatch_action(action)))

        # We use return_exceptions so that this function can't throw
        await asyncio.gather(*tasks, return_exceptions=False)

    # Normal hooks

    def add_command(self, cmd: Command):
        self.commands[cmd.name] = cmd

    def add_periodic(self, func, periodic: float):
        self.periodics[func.__name__] = Periodic(self, func, periodic)

    def add_event(self, func, event_type: EventType | list[EventType]):
        self.events[func.__name__] = Event(self, event_type, func)

    def add_middleware(
        self, func: MiddlewareFunc, priority: int, m_type: MiddlewareType
    ):
        if m_type == MiddlewareType.LOCAL:
            self.local_md[func.__name__] = Middleware(self, func, m_type, priority)
        else:
            self.global_md[func.__name__] = Middleware(self, func, m_type, priority)

    def add_temporary_msg_react(self, msg_id: str, func):
        if msg_id in self.rolling_handlers:  # Delete duplicate message handler
            self.rolling_handlers.remove(msg_id)
        self.rolling_handlers.append(MessageReact(self, msg_id, func))

    def del_temporary_msg_react(self, msg_id: str):
        if msg_id in self.rolling_handlers:
            self.rolling_handlers.remove(msg_id)

    def add_permanent_msg_react(self, msg_id: str, func):
        # temporary handlers might be "upgraded" to permanent ones
        # keep track of that to avoid duplication
        # TODO: test
        self.del_temporary_msg_react(msg_id)

        if msg_id in self.permanent_handlers:  # Delete duplicate message handler
            self.permanent_handlers.remove(msg_id)
        self.permanent_handlers.append(MessageReact(self, msg_id, func))

    def del_permanent_msg_react(self, msg_id: str):
        if msg_id in self.permanent_handlers:
            self.permanent_handlers.remove(msg_id)

    def del_msg_react(self, msg_id: str):
        self.del_temporary_msg_react(msg_id)
        self.del_permanent_msg_react(msg_id)
        for child in self.children:
            child.del_msg_react(msg_id)

    @property
    def temporary_msg_react_handlers(self) -> list[MessageReact]:
        rez = self.rolling_handlers.copy()
        for child in self.children:
            rez.extend(child.temporary_msg_react_handlers)
        return rez

    def find_temporary_msg_react(self, msg_id: str) -> Optional[MessageReact]:
        # TODO: Test
        handlers = self.temporary_msg_react_handlers
        if msg_id in handlers:
            return handlers[handlers.index(msg_id)]

    @property
    def permanent_msg_react_handlers(self) -> list[MessageReact]:
        rez = self.permanent_handlers.copy()
        for child in self.children:
            rez.extend(child.permanent_msg_react_handlers)
        return rez

    def find_permanent_msg_react(self, msg_id: str) -> Optional[MessageReact]:
        # TODO: Test
        handlers = self.permanent_msg_react_handlers
        if msg_id in handlers:
            return handlers[handlers.index(msg_id)]

    # Server Storage
    def server_storage(self, server_id: Optional[str]):
        if not server_id:
            return None
        return storage.server_storage(server_id, self.storage_name)

    def data_location(self, server_id: Optional[str]):
        if not server_id:
            return None
        return storage.data_location(server_id, self.storage_name)

    @property
    def hook_storage(self):
        return storage.hook_storage(self.storage_name)

    # Traditional function decorators

    # command returns a decorator for adding commands
    # Unlike the old decorator, it doesn't support having non-keyword args or being called directly, in order to simplify stuff
    def command(self, *args, **kwargs):
        if len(args) > 0:
            raise TypeError(
                "Hook.command must be used as a function that returns a decorator."
            )

        def wrap(func):
            self.add_command(Command(self, func.__name__, func, **kwargs))
            return func

        return wrap

    def periodic(self, period: float):
        if callable(period):
            raise TypeError(
                "Hook.periodic must be used as a function that returns a decorator."
            )

        def wrap(func):
            self.add_periodic(func, period)
            return func

        return wrap

    def event(self, event_type: EventType | list[EventType]):
        if callable(event_type):
            raise TypeError(
                "Hook.event must be used as a function that returns a decorator."
            )

        def wrap(func):
            self.add_event(func, event_type)
            return func

        return wrap

    def global_middleware(self, priority: int):
        if callable(priority):
            raise TypeError(
                "Hook.global_middleware must be used as a function that returns a decorator."
            )

        def wrap(func):
            self.add_middleware(func, priority, MiddlewareType.GLOBAL)
            return func

        return wrap

    def local_middleware(self, priority: int):
        if callable(priority):
            raise TypeError(
                "Hook.local_middleware must be used as a function that returns a decorator."
            )

        def wrap(func):
            self.add_middleware(func, priority, MiddlewareType.LOCAL)
            return func

        return wrap
