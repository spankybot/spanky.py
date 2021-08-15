# Delay checking for typing (TODO: remove when bot runs on python 3.10)
from __future__ import annotations

from typing import Any, Callable, Optional
from spanky.hook2.event import EventType
from spanky.hook2.storage import Storage
import asyncio
import time
import random
import inspect
import threading
from enum import Enum

# copy-paste from old plugin manager
import logging
logger = logging.getLogger('spanky')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


def required_args(func) -> list[str]:
    args = inspect.getfullargspec(func)[0]
    if not args:
        return []
    return [arg for arg in args if not arg.startswith('_')]

class Hooklet():
    def __init__(self, hook: Hook, hooklet_id: str, func):
        self.hook: Hook = hook
        self.hooklet_id: str = hooklet_id
        self.func = func
        
    def get_args(self, action: Action) -> Optional[list[Any]]:
        args = []
        for arg in required_args(self.func):
            if hasattr(action, arg):
                val = getattr(action, arg)
                args.append(val)
            elif hasattr(action._raw, arg):
                val = getattr(action._raw, arg)
                args.append(val)
            elif arg == 'storage':
                if not action.server_id:
                    print(f"Hooklet {self.hooklet_id} asked for storage with an action with no server, cancelling execution. This might be a bug!")
                    return None
                storage = self.hook.server_storage(action.server_id)
                args.append(storage)
            elif arg == 'action':
                args.append(action)
            elif arg == 'event':
                args.append(action._raw)
            else:
                print(f"Hooklet {self.hooklet_id} asked for invalid argument '{arg}', cancelling execution")
                return None
        return args

    async def handle(self, action: Action):
        try:
            args = self.get_args(action)
            if args is None:
                return None
            
            if asyncio.iscoroutinefunction(self.func):
                rez = await self.func(*args)
            else:
                rez = self.func(*args)

            realRez = None
            if type(rez) is str:
                realRez = rez
            elif type(rez) is list:
                try:
                    realRez = "\n".join(realRez)
                except:
                    pass
            elif rez != None:
                print(f"Unknown type {type(rez)} returned by hooklet {self.hooklet_id}")

            if realRez != None:
                replyFunc = None
                if hasattr(action, 'reply'):
                    replyFunc = action.reply
                elif hasattr(action._raw, 'reply'):
                    replyFunc = action._raw.reply

                if replyFunc:
                    replyFunc(rez) 
                else:
                    print(f"Missing reply function, but got output '{realRez!s}'")
        except:
            import traceback
            traceback.print_exc()

class Command(Hooklet):
    # Creates a new Command hooklet. Note that, if kwargs has a "name", then it will use that name instead 
    def __init__(self, hook: Hook, fname: str, func, **kwargs):
        super().__init__(hook, f'{hook.hook_id}_{fname}', func)
        self.args: dict[str, Any] = kwargs
        self.name: str = self.args.pop("name", fname)
        # TODO
        #self.aliases: list[str] = self.args.pop("aliases", [])

        self.can_pm: bool = self.args.pop("can_pm", False)
        self.pm_only: bool = self.args.pop("pm_only", False)
        if self.pm_only:
            self.can_pm = True

        if self.name == "":
            self.name = func.__name__

class Periodic(Hooklet):
    def __init__(self, hook: Hook, func, interval: float):
        super().__init__(hook, f'{hook.hook_id}_{func.__name__}', func)
        self.interval: float = interval
        self.last_time = time.time()

class Event(Hooklet):
    def __init__(self, hook: Hook, event_type: EventType, func):
        super().__init__(hook, f'{hook.hook_id}_event_{func.__name__}', func)
        self.event_type = event_type

    def __str__(self):
        return f"EventHooklet[{self.event_type=}]"

class MiddlewareType(Enum):
    LOCAL = 1
    GLOBAL = 2

class MiddlewareResult(Enum):
    CONTINUE = 1
    DENY = 2

MiddlewareFunc = Callable[['Action', Hooklet], Optional[MiddlewareResult]]

class Middleware(Hooklet):
    def __init__(self, hook: Hook, func: MiddlewareFunc, m_type: MiddlewareType, priority: int):
        super().__init__(hook, f'{hook.hook_id}_middleware_{func.__name__}', func)
        self.m_type: MiddlewareType = m_type
        # Redefine for typing support
        self.func: MiddlewareFunc = func
        self.priority: int = priority

    async def handle(self, action: Action, hooklet: Hooklet) -> MiddlewareResult:
        if asyncio.iscoroutinefunction(self.func):
            rez = await self.func(action, hooklet)
        else:
            rez = self.func(action, hooklet)
        if not rez:
            rez = MiddlewareResult.CONTINUE
        return rez

class Hook():
    hash = random.randint(0, 2**31)

    def __init__(self, hook_id: str, *, parent_hook: Optional[Hook]=None):
        self.hook_id: str = hook_id
        
        # Hooklet dicts
        self.commands: dict[str, Command] = {}
        self.periodics: dict[str, Periodic] = {}
        self.events: dict[str, Event] = {}
        self.global_middleware: dict[str, Middleware] = {}
        self.local_middleware: dict[str, Middleware] = {}
        
        # Storage object
        self.storage: Storage = Storage(hook_id)

        # Tree 
        self.parent_hook: Optional[Hook] = parent_hook 
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
    def all_events(self) -> dict[str, Event]:
        events = self.events.copy()
        for child in self.children:
            events |= child.all_events
        return events
    
    @property
    def all_global_middleware(self) -> dict[str, Middleware]:
        global_md = self.global_middleware.copy()
        for child in self.children:
            global_md |= child.all_global_middleware
        return global_md

    @property
    def all_local_middleware(self) -> dict[str, Middleware]:
        local_md = self.local_middleware.copy()
        for child in self.children:
            local_md = child.all_local_middleware
        return local_md
    
    # TODO: Do this nicer
    async def run_middleware(self, action: Action, hooklet: Hooklet):
        gmds: dict[str, Middleware] = dict(sorted(self.all_global_middleware.items(), key=lambda item: item[1].priority))
        for md in gmds.values():
            rez = await md.handle(action, hooklet)
            if rez == MiddlewareResult.DENY:
                reply = action.get_reply() 
                if reply:
                    reply("Event blocked by middleware")
                else:
                    print("Event blocked by middleware")
                return
        lmds: dict[str, Middleware] = dict(sorted(self.all_local_middleware.items(), key=lambda item: item[1].priority))
        for md in lmds.values():
            rez = await md.handle(action, hooklet)
            if rez == MiddlewareResult.DENY:
                reply = action.get_reply() 
                if reply:
                    reply("Event blocked by middleware")
                else:
                    print("Event blocked by middleware")
                return
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
        if self.hook_id == 'bot_hook':
            print(self.hook_id, action)
        
        coros = []

        if action.event_type is EventType.command:
            # Command trigger
            action: ActionCommand = action
            if action.triggered_command in self.commands.keys():
                # Do with middleware
                hooklet = self.commands[action.triggered_command]
                coros.append(self.run_middleware(action, hooklet))
        elif action.event_type is EventType.periodic:
            # Periodic trigger
            action: ActionPeriodic = action
            for periodic in self.periodics.values():
                if periodic.hooklet_id == action.target:
                    coros.append(periodic.handle(action))
        
        # Gobble all matching event coroutines
        for event_hooklet in self.events.values():
            if event_hooklet.event_type == action.event_type:
                coros.append(event_hooklet.handle(action))
        
        # Gobble children dispatch coroutines
        for child in self.children:
            coros.append(child.dispatch_action(action))

        # We use return_exceptions so that this function can't throw
        await asyncio.gather(*coros, return_exceptions=True)

    # Command Hooks

    def add_command(self, func, **kwargs):
        print("DEBUG - Loaded Command FROM HOOK2 WOOO")
        self.commands[func.__name__] = Command(self, func.__name__, func, **kwargs)

    #def remove_command(self, name: str):
    #    if name not in self.commands:
    #        raise Exception("Stupid")
    #    del self.commands[name]

    #def get_command(self, name: str):
    #    if name not in self.commands:
    #        return None
    #    return self.commands[name]

    # Periodic Hooks
    def add_periodic(self, func, periodic: float):
        self.periodics[func.__name__] = Periodic(self, func, periodic)

    def add_event(self, func, event_type: EventType):
        self.events[func.__name__] = Event(self, event_type, func)

    def add_middleware(self, func: MiddlewareFunc, priority: int, m_type: MiddlewareType):
        if m_type == MiddlewareType.LOCAL:
            self.local_middleware[func.__name__] = Middleware(self, func, m_type, priority)
        else:
            self.global_middleware[func.__name__] = Middleware(self, func, m_type, priority)

    # Server Storage
    def server_storage(self, server):
        # TODO
        pass

    @property
    def hook_storage(self):
        # TODO
        pass
    
    @property
    def global_storage(self):
        # TODO
        pass

    # Traditional function decorators

    # command returns a decorator for adding commands
    # Unlike the old decorator, it doesn't support having non-keyword args or being called directly, in order to simplify stuff
    def command(self, *args, **kwargs):
        if len(args) > 0:
            raise TypeError("Hook.command must be used as a function that returns a decorator.")
        return lambda func: self.add_command(func, **kwargs)

    def periodic(self, period: float):
        if callable(period):
            raise TypeError("Hook.periodic must be used as a function that returns a decorator.")
        return lambda func: self.add_periodic(func, period)

    def event(self, event_type: EventType):
        if callable(event_type):
            raise TypeError("Hook.event must be used as a function that returns a decorator.")
        return lambda func: self.add_event(func, event_type)

    def global_middleware(self, priority: int):
        if callable(priority):
            raise TypeError("Hook.global_middleware must be used as a function that returns a decorator.")
        return lambda func: self.add_middleware(func, priority, MiddlewareType.GLOBAL)

    def local_middleware(self, priority: int):
        if callable(priority):
            raise TypeError("Hook.local_middleware must be used as a function that returns a decorator.")
        return lambda func: self.add_middleware(func, priority, MiddlewareType.LOCAL)

# TODO
class Action:
    """Action is the base class for an action"""
    def __init__(self, event_type: EventType, bot, event):
        self.bot = bot
        self.event_type = event_type
        self._raw = event
        self.context = {}

        self.server_id: Optional[str] = None
        if hasattr(event, "server_id"):
            self.server_id = event.server_id
        if hasattr(event, "server"):
            self.server_id = event.server.id

    def __str__(self):
        return f"Action[{self.event_type=!s} {self.server_id=}]"

class ActionCommand(Action):
    def __init__(self, bot, event, text: str, command: str):
        super().__init__(EventType.command, bot, event)
        print(f"Init command with text '{text}'")
        self.text: str = text
        self.triggered_command: str = command
        print(event)

    def reply(self, text):
        self._raw.reply(text)
        

class ActionPeriodic(Action):
    def __init__(self, bot, target):
        super().__init__(EventType.periodic, bot, {})
        self.target = target

class ActionEvent(Action):
    def __init__(self, bot, event, event_type):
        super().__init__(event_type, bot, event)

class ActionOnReady(Action):
    def __init__(self, bot, server):
        super().__init__(EventType.on_ready, bot, {})
        self.server = server

