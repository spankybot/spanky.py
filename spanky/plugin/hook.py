import inspect
import re
import collections

from spanky.hook2 import Hook, EventType, Command, Event, Periodic


def command(**kwargs):
    def do_func(func):
        func.__hk1_wrapped = True
        func.__hk1_list = "commands"
        func.__hk1_key = func.__name__
        func.__hk1_hooklet = lambda hook: Command(hook, func.__name__, func, **kwargs)
        return func

    return do_func


def event(event_type: EventType):
    def do_func(func):
        func.__hk1_wrapped = True
        func.__hk1_list = "events"
        func.__hk1_key = func.__name__
        func.__hk1_hooklet = lambda hook: Event(hook, event_type, func)
        return func

    return do_func


def periodic(period: float):
    def do_func(func):
        func.__hk1_wrapped = True
        func.__hk1_list = "periodics"
        func.__hk1_key = func.__name__
        func.__hk1_hooklet = lambda hook: Periodic(hook, func, period)
        return func

    return do_func


def on_start():
    return event(EventType.on_start)


def on_ready():
    return event(EventType.on_ready)


def on_connection_ready():
    return event(EventType.on_conn_ready)
