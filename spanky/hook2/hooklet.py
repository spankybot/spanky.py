# Delay checking for typing (TODO: remove when bot runs on python 3.10)
from __future__ import annotations
from random import sample
from typing import TYPE_CHECKING
import time
import nextcord

from spanky.hook2.slash import SArg

if TYPE_CHECKING:
    from .hook2 import Hook
    from .actions import Action, ActionCommand
    from .event import EventType
    from asyncio import Task
from enum import Enum
from spanky.hook2 import storage
from . import arg_parser

import asyncio
import inspect
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor()


async def schedule_func(func, /, *args):
    loop = asyncio.get_running_loop()
    if inspect.iscoroutinefunction(func):
        return await func(*args)
    else:
        return await loop.run_in_executor(executor, func, *args)


def required_args(func) -> list[str]:
    args = inspect.getfullargspec(func)[0]
    if not args:
        return []
    return [arg for arg in args if not arg.startswith("_")]


class Hooklet:
    def __init__(self, hook: Hook, hooklet_id: str, func):
        self.hook: Hook = hook
        self.hooklet_id: str = hooklet_id
        self.func = func
        self.slash_args = []

    def __storage_getter(self, server_id: str, storage_name: Optional[str] = None):
        if storage_name == None:
            storage_name = self.hook.storage_name
        return storage.server_storage(server_id, storage_name)

    def __get_args(self, action: Action) -> Optional[list[Any]]:
        args = []
        for arg in required_args(self.func):
            if hasattr(action, arg):
                val = getattr(action, arg)
                args.append(val)
            elif hasattr(action._raw, arg):
                val = getattr(action._raw, arg)
                args.append(val)
            elif hasattr(action, "context") and arg in getattr(action, "context"):
                val = getattr(action, "context")[arg]
                args.append(val)
            elif arg == "storage":
                if not action.server_id:
                    print(
                        f"Hooklet {self.hooklet_id} asked for storage with an action with no server, cancelling execution. This might be a bug!"
                    )
                    return None
                storage = self.hook.server_storage(action.server_id)
                args.append(storage)
            elif arg == "storage_loc":
                if not action.server_id:
                    print(
                        f"Hooklet {self.hooklet_id} asked for storage_loc with an action with no server, cancelling execution. This might be a bug!"
                    )
                    return None
                storage_loc = self.hook.data_location(action.server_id)
                args.append(storage_loc)
            elif arg == "unique_storage":
                args.append(self.hook.hook_storage)
            elif arg == "storage_getter":
                args.append(self.__storage_getter)
            elif arg == "action":
                args.append(action)
            elif arg == "event":
                args.append(action._raw)
            elif arg == "hook":
                args.append(self.hook)
            elif arg == "self":
                continue
            else:
                print(
                    f"Hooklet {self.hooklet_id} asked for invalid argument '{arg}', cancelling execution"
                )
                return None
        return args

    async def handle(self, action: Action):
        try:
            args = self.__get_args(action)
            if args is None:
                return None

            rez = await schedule_func(self.func, *args)

            realRez = None
            if type(rez) is str:
                realRez = rez
            elif type(rez) is list:
                try:
                    realRez = "\n".join(realRez)
                except:
                    pass
            elif type(rez) is nextcord.File:
                await action.channel._raw.send(file=rez)
            elif rez != None:
                print(f"Unknown type {type(rez)} returned by hooklet {self.hooklet_id}")

            if realRez != None:
                replyFunc = None
                if hasattr(action, "reply"):
                    replyFunc = action.reply
                elif hasattr(action._raw, "reply"):
                    replyFunc = action._raw.reply

                if replyFunc:
                    replyFunc(rez)
                else:
                    print(f"Missing reply function, but got output '{realRez!s}'")
        except:
            import traceback

            traceback.print_exc()

    def get_subcommands(self) -> list:
        """
        Returns a list of subcommands.
        This returns empty by default and needs to be overriden by child classes.
        """
        return []


class Command(Hooklet):
    # Creates a new Command hooklet. Note that, if kwargs has a "name", then it will use that name instead
    def __init__(self, hook: Hook, fname: str, func, **kwargs):
        super().__init__(hook, f"{hook.hook_id}_{fname}", func)
        self.args: dict[str, Any] = kwargs
        self.name: str = self.args.pop("name", fname)
        self.aliases: list[str] = self.args.pop("aliases", [])

        # Add slash args, if empty or not
        self.slash_args = kwargs.get("slash_args", [])

        if len(self.slash_args) == 0:
            # Check if the function has docstring slash params defined
            params = []
            if self.func.__doc__:
                params = arg_parser.parse(self.func.__doc__)

            # If no explicit docstring params:
            # If 'text' is requested and no explicit slash params are set, add a string argument
            if len(params) == 0:
                if "text" in required_args(self.func):
                    self.slash_args.append(SArg("text", str))
            else:
                # If parameters are found, create SArg objects for each one
                for param in params:
                    values = param.validate()
                    self.slash_args.append(SArg.from_parser(values))

        if not isinstance(self.aliases, list):
            self.aliases = [self.aliases]

        if self.name == "":
            self.name = func.__name__

    def get_doc(self, no_format=False):
        doc = self.args.get("doc", self.func.__doc__)
        if doc == None:
            if no_format:
                return None
            fmt: str = self.args.get("format", None)
            if fmt == None:
                return "No description provided."
            return " ".join(f"<{arg}>" for arg in fmt.split())
        return doc.strip()


class Periodic(Hooklet):
    def __init__(self, hook: Hook, func, interval: float):
        super().__init__(hook, f"{hook.hook_id}_{func.__name__}", func)
        self.interval: float = interval
        self.last_time = time.time()


class Event(Hooklet):
    def __init__(self, hook: Hook, event_type: EventType | list[EventType], func):
        super().__init__(hook, f"{hook.hook_id}_event_{func.__name__}", func)
        self.event_types: list[EventType] = []
        if isinstance(event_type, list):
            self.event_types = event_type
        else:
            self.event_types = [event_type]

    def __str__(self):
        return f"EventHooklet[{self.event_types=}]"


class MiddlewareType(Enum):
    LOCAL = 1
    GLOBAL = 2


class MiddlewareResult(Enum):
    CONTINUE = 1
    DENY = 2


class Middleware(Hooklet):
    def __init__(
        self, hook: Hook, func: MiddlewareFunc, m_type: MiddlewareType, priority: int
    ):
        super().__init__(hook, f"{hook.hook_id}_middleware_{func.__name__}", func)
        self.m_type: MiddlewareType = m_type
        # Redefine for typing support
        self.func: MiddlewareFunc = func
        self.priority: int = priority

    async def handle(
        self, action: ActionCommand, hooklet: Command
    ) -> (MiddlewareResult, str):
        if inspect.iscoroutinefunction(self.func):
            rez = await self.func(action, hooklet)
        else:
            rez = self.func(action, hooklet)
        if not rez:
            rez = MiddlewareResult.CONTINUE
        if not (isinstance(rez, list) or isinstance(rez, tuple)):
            if rez == MiddlewareResult.CONTINUE:
                rez = (rez, "")
            else:
                rez = (rez, "Command blocked for unknown reason")
        return rez
