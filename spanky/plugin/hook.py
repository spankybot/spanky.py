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


'''
def command(*args, **kwargs):
    """External command decorator. Can be used directly as a decorator, or with args to return a decorator.
    :type param: str | list[str] | function
    """

    def _command_hook(func, alias_param=None):
        hook = _get_hook(func, "command")
        if hook is None:
            hook = _CommandHook(func)
            _add_hook(func, hook)

        hook.add_hook(alias_param, kwargs)
        return func

    if len(args) == 1 and callable(args[0]):  # this decorator is being used directly
        return _command_hook(args[0])
    else:  # this decorator is being used indirectly, so return a decorator function
        return lambda func: _command_hook(func, alias_param=args)


def event(types_param, **kwargs):
    """External event decorator. Must be used as a function to return a decorator
    :type types_param: cloudbot.event.EventType | list[cloudbot.event.EventType]
    """

    def _event_hook(func):
        hook = _get_hook(func, "event")
        if hook is None:
            hook = _EventHook(func)
            _add_hook(func, hook)

        hook.add_hook(types_param, kwargs)
        return func

    if callable(types_param):  # this decorator is being used directly, which isn't good
        raise TypeError("@event() must be used as a function that returns a decorator")
    else:  # this decorator is being used as a function, so return a decorator
        return lambda func: _event_hook(func)

def sieve(param=None, **kwargs):
    """External sieve decorator. Can be used directly as a decorator, or with args to return a decorator
    :type param: function | None
    """

    def _sieve_hook(func):
        hook = _get_hook(func, "sieve")
        if hook is None:
            hook = _Hook(func, "sieve")  # there's no need to have a specific SieveHook object
            _add_hook(func, hook)

        hook._add_hook(kwargs)
        return func

    if callable(param):
        return _sieve_hook(param)
    else:
        return lambda func: _sieve_hook(func)


def periodic(interval, **kwargs):
    """External on_start decorator. Can be used directly as a decorator, or with args to return a decorator
    :type param: function | None
    """

    def _periodic_hook(func):
        hook = _get_hook(func, "periodic")
        if hook is None:
            hook = _PeriodicHook(func)
            _add_hook(func, hook)

        hook.add_hook(interval, kwargs)
        return func

    if callable(interval):  # this decorator is being used directly, which isn't good
        raise TypeError("@periodic() hook must be used as a function that returns a decorator")
    else:  # this decorator is being used as a function, so return a decorator
        return lambda func: _periodic_hook(func)

def on_start(param=None, **kwargs):
    """External on_start decorator. Can be used directly as a decorator, or with args to return a decorator
    :type param: function | None
    """

    def _on_start_hook(func):
        hook = _get_hook(func, "on_start")
        if hook is None:
            hook = _Hook(func, "on_start")
            _add_hook(func, hook)

        hook._add_hook(kwargs)
        return func

    if callable(param):
        return _on_start_hook(param)
    else:
        return lambda func: _on_start_hook(func)

def on_ready(param=None, **kwargs):
    """external on_ready decorator. Can be used directly as a decorator, or with args to return a decorator
    :type param: function | none
    """

    def _on_ready_hook(func):
        hook = _get_hook(func, "on_ready")
        if hook is None:
            hook = _Hook(func, "on_ready")
            _add_hook(func, hook)

        hook._add_hook(kwargs)
        return func

    if callable(param):
        return _on_ready_hook(param)
    else:
        return lambda func: _on_ready_hook(func)

def on_connection_ready(param=None, **kwargs):
    """external on_connection_ready decorator. can be used directly as a decorator, or with args to return a decorator
    :type param: function | none
    """

    def _on_connection_ready_hook(func):
        hook = _get_hook(func, "on_connection_ready")
        if hook is None:
            hook = _Hook(func, "on_connection_ready")
            _add_hook(func, hook)

        hook._add_hook(kwargs)
        return func

    if callable(param):
        return _on_connection_ready_hook(param)
    else:
        return lambda func: _on_connection_ready_hook(func)
'''
