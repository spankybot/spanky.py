# Delay checking for typing (TODO: remove when bot runs on python 3.10)
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .hook2 import Hook
    from .actions import Action, ActionCommand
    from .event import EventType
from enum import Enum
import inspect

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
            
            if inspect.iscoroutinefunction(self.func):
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

class Middleware(Hooklet):
    def __init__(self, hook: Hook, func: MiddlewareFunc, m_type: MiddlewareType, priority: int):
        super().__init__(hook, f'{hook.hook_id}_middleware_{func.__name__}', func)
        self.m_type: MiddlewareType = m_type
        # Redefine for typing support
        self.func: MiddlewareFunc = func
        self.priority: int = priority

    async def handle(self, action: ActionCommand, hooklet: Command) -> MiddlewareResult:
        if inspect.iscoroutinefunction(self.func):
            rez = await self.func(action, hooklet)
        else:
            rez = self.func(action, hooklet)
        if not rez:
            rez = MiddlewareResult.CONTINUE
        return rez

