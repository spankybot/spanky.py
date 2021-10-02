import inspect
import re
import collections

from spanky.hook2 import Hook, EventType, Command, Event, Periodic

# Replaced for the hook1 wrapper, TODO: finish the simple hook1 wrapper

legacy_handler = Hook("hook1_legacy_handler")

hooks: dict[str, Hook] = {}


def format_filename(name: str) -> str:
    return name.replace(".py", "").replace("/", "_")


def get_hook(filename: str) -> Hook:
    filename = format_filename(filename)
    if filename in hooks.keys():
        return hooks[filename]

    hook = Hook(filename, parent_hook=legacy_handler)
    hooks.update({filename: hook})
    return hook


def command(**kwargs):
    import inspect

    filename = inspect.stack()[1].filename
    filename = filename[filename.find("plugins") :]

    def do_func(func):
        hook = get_hook(filename)
        hook.add_command(func.__name__, Command(hook, func.__name__, func, **kwargs))
        return func

    return do_func


def event(event_type: EventType):
    import inspect

    filename = inspect.stack()[1].filename
    filename = filename[filename.find("plugins") :]

    def do_func(func):
        hook = get_hook(filename)
        hook.add_event(func, event_type)
        return func

    return do_func


def periodic(period: float):
    import inspect

    filename = inspect.stack()[1].filename
    filename = filename[filename.find("plugins") :]

    def do_func(func):
        hook = get_hook(filename)
        hook.add_periodic(func, period)
        return func

    return do_func


def on_start(**kwargs):
    import inspect

    filename = inspect.stack()[1].filename
    filename = filename[filename.find("plugins") :]

    def do_func(func):
        hook = get_hook(filename)
        hook.add_event(func, EventType.on_start)
        return func

    return do_func


def on_ready(**kwargs):
    import inspect

    filename = inspect.stack()[1].filename
    filename = filename[filename.find("plugins") :]

    def do_func(func):
        hook = get_hook(filename)
        hook.add_event(func, EventType.on_ready)
        return func

    return do_func


def on_connection_ready(**kwargs):
    import inspect

    filename = inspect.stack()[1].filename
    filename = filename[filename.find("plugins") :]

    def do_func(func):
        hook = get_hook(filename)
        hook.add_event(func, EventType.on_conn_ready)
        return func

    return do_func
