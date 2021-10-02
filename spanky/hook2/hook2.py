# Delay checking for typing (TODO: remove when bot runs on python 3.10)
from __future__ import annotations

from spanky.hook2 import storage
from spanky.hook2.complex_cmd import ComplexCommand
from .hooklet import (
    Command,
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
    hash = random.randint(0, 2 ** 31)

    def __init__(
        self,
        hook_id: str,
        *,
        storage_name: str = "",
        parent_hook: Optional[Hook] = None,
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
        self.storage: storage.Storage = storage.Storage(self.storage_name)

        # Tree
        self.parent_hook: Optional[Hook] = parent_hook
        if self.parent_hook != None and not self.parent_hook.has_child(self):
            self.parent_hook.add_child(self)

        self.children: list[Hook] = []

    def __del__(self):
        self.unload()

    # unload unloads the entire tree
    def unload(self):
        if self.parent_hook:
            self.parent_hook.remove_child(self)
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
        print(mds.keys())
        for md in mds.values():
            rez, msg = await md.handle(action, hooklet)
            if rez == MiddlewareResult.DENY:
                print("blocking from", md.hooklet_id, "with reason", msg)
                action.reply(msg)
                return
        # Run middleware for the subcommand
        if isinstance(hooklet, ComplexCommand):
            cmd, action = hooklet.get_cmd(action)
            for md in mds.values():
                rez, msg = await md.handle(action, cmd)
                if rez == MiddlewareResult.DENY and msg != "":
                    action.reply(msg, timeout=15)
                    return
            await cmd.handle(action)
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

    # remove_child removes a child hook if it is directly underneath the current node.
    def remove_child(self, hook: Hook):
        try:
            self.children.remove(hook)
        except:
            pass

    # Event propagation
    # The return of this function marks the finalization of propagating across the entire subtree
    async def dispatch_action(self, action: Action):
        if self.hook_id == "bot_hook" and not isinstance(action, ActionPeriodic):
            print(self.hook_id, action)

        tasks = []

        if action.event_type is EventType.command:
            # Command trigger
            action: ActionCommand = action
            if action.triggered_command in self.commands.keys():
                # Do with middleware
                hooklet = self.commands[action.triggered_command]
                tasks.append(
                    asyncio.create_task(self.run_middleware(action, hooklet), name="")
                )
        elif action.event_type is EventType.periodic:
            # Periodic trigger
            action: ActionPeriodic = action
            for periodic in self.periodics.values():
                if periodic.hooklet_id == action.target:
                    tasks.append(asyncio.create_task(periodic.handle(action)))

        # Gobble all matching event coroutines
        for event_hooklet in self.events.values():
            if event_hooklet.event_type == action.event_type:
                tasks.append(asyncio.create_task(event_hooklet.handle(action)))

        # Gobble children dispatch coroutines
        for child in self.children:
            tasks.append(asyncio.create_task(child.dispatch_action(action)))

        # We use return_exceptions so that this function can't throw
        x = await asyncio.gather(*tasks, return_exceptions=False)

    # Command Hooks

    def add_command(self, name: str, cmd: Command):
        self.commands[name] = cmd
        # self.commands[func.__name__] = Command(self, func.__name__, func, **kwargs)

    # Periodic Hooks
    def add_periodic(self, func, periodic: float):
        self.periodics[func.__name__] = Periodic(self, func, periodic)

    def add_event(self, func, event_type: EventType):
        self.events[func.__name__] = Event(self, event_type, func)

    def add_middleware(
        self, func: MiddlewareFunc, priority: int, m_type: MiddlewareType
    ):
        if m_type == MiddlewareType.LOCAL:
            self.local_md[func.__name__] = Middleware(self, func, m_type, priority)
        else:
            self.global_md[func.__name__] = Middleware(self, func, m_type, priority)

    # Server Storage
    def server_storage(self, server_id: str):
        return self.storage.server_storage(server_id)

    @property
    def hook_storage(self):
        return self.storage.hook_storage

    @property
    def global_storage(self):
        return storage.global_storage

    # Traditional function decorators

    # command returns a decorator for adding commands
    # Unlike the old decorator, it doesn't support having non-keyword args or being called directly, in order to simplify stuff
    def command(self, *args, **kwargs):
        if len(args) > 0:
            raise TypeError(
                "Hook.command must be used as a function that returns a decorator."
            )
        return lambda func: self.add_command(
            func.__name__, Command(self, func.__name__, func, **kwargs)
        )

    def periodic(self, period: float):
        if callable(period):
            raise TypeError(
                "Hook.periodic must be used as a function that returns a decorator."
            )
        return lambda func: self.add_periodic(func, period)

    def event(self, event_type: EventType):
        if callable(event_type):
            raise TypeError(
                "Hook.event must be used as a function that returns a decorator."
            )
        return lambda func: self.add_event(func, event_type)

    def global_middleware(self, priority: int):
        if callable(priority):
            raise TypeError(
                "Hook.global_middleware must be used as a function that returns a decorator."
            )
        return lambda func: self.add_middleware(func, priority, MiddlewareType.GLOBAL)

    def local_middleware(self, priority: int):
        if callable(priority):
            raise TypeError(
                "Hook.local_middleware must be used as a function that returns a decorator."
            )
        return lambda func: self.add_middleware(func, priority, MiddlewareType.LOCAL)
