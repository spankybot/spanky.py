import time
import inspect
import sqlalchemy
import logging
from spanky.plugin.hook_parameters import extract_params

from spanky import database

logger = logging.getLogger("spanky")


class Hook:
    """
    Each hook is specific to one function. This class is never used by itself, rather extended.

    :type type; str
    :type plugin: Plugin
    :type function: callable
    :type function_name: str
    :type required_args: list[str]
    :type threaded: bool
    :type permissions: list[str]
    :type single_thread: bool
    """

    def __init__(self, _type, plugin, func_hook):
        """
        :type _type: str
        :type plugin: Plugin
        :type func_hook: hook._Hook
        """
        self.type = _type
        self.plugin = plugin
        self.function = func_hook.function
        self.function_name = self.function.__name__

        self.required_args = inspect.getfullargspec(self.function)[0]
        if self.required_args is None:
            self.required_args = []

        # don't process args starting with "_"
        self.required_args = [
            arg for arg in self.required_args if not arg.startswith("_")
        ]

        if inspect.iscoroutine(self.function) or inspect.iscoroutinefunction(
            self.function
        ):
            self.threaded = False
        else:
            self.threaded = True

        self.permissions = func_hook.kwargs.pop("permissions", [])
        if type(self.permissions) is not list:
            self.permissions = [self.permissions]

        self.format = func_hook.kwargs.pop("format", None)
        self.single_thread = func_hook.kwargs.pop("singlethread", False)
        self.server_id = func_hook.kwargs.pop("server_id", None)
        if isinstance(self.server_id, int):
            self.server_id = str(self.server_id)

        self.given_cmd_params = func_hook.kwargs.pop("params", None)

        self.param_list = None
        if self.given_cmd_params is not None:
            self.param_list = extract_params(self.given_cmd_params)

        if func_hook.kwargs:
            # we should have popped all the args, so warn if there are any left
            logger.warning(
                "Ignoring extra args {} from {}".format(
                    func_hook.kwargs, self.description
                )
            )

    def has_server_id(self, sid):
        if type(self.server_id) == str:
            return self.server_id == sid
        elif type(self.server_id) == list:
            return sid in self.server_id

        return None

    @property
    def description(self):
        return "{}:{}".format(self.plugin.name, self.function_name)

    def __repr__(self):
        return "type: {}, plugin: {}".format(self.type, self.plugin.name)


class CommandHook(Hook):
    """
    :type name: str
    :type aliases: list[str]
    :type doc: str
    :type auto_help: bool
    """

    def __init__(self, plugin, cmd_hook):
        """
        :type plugin: Plugin
        :type cmd_hook: cloudbot.util.hook._CommandHook
        """
        self.auto_help = cmd_hook.kwargs.pop("autohelp", True)

        self.can_pm = cmd_hook.kwargs.pop("can_pm", False)
        self.pm_only = cmd_hook.kwargs.pop("pm_only", False)
        if self.pm_only:
            self.can_pm = True

        self.name = cmd_hook.main_alias.lower()
        self.aliases = cmd_hook.kwargs.pop("aliases", []) + [
            alias.lower() for alias in cmd_hook.aliases
        ]
        self.aliases.remove(self.name)
        self.aliases.insert(
            0, self.name
        )  # make sure the name, or 'main alias' is in position 0
        self.doc = cmd_hook.doc

        super().__init__("command", plugin, cmd_hook)

    def __repr__(self):
        return "Command[name: {}, aliases: {}, {}]".format(
            self.name, self.aliases[1:], Hook.__repr__(self)
        )

    def __str__(self):
        return "command {} from {}".format(
            "/".join(self.aliases), self.plugin.file_name
        )


class PeriodicHook(Hook):
    """
    :type interval: int
    """

    def __init__(self, plugin, periodic_hook):
        """
        :type plugin: Plugin
        :type periodic_hook: cloudbot.util.hook._PeriodicHook
        """

        self.interval = periodic_hook.interval
        self.initial_interval = periodic_hook.kwargs.pop(
            "initial_interval", self.interval
        )
        self.last_time = time.time()

        super().__init__("periodic", plugin, periodic_hook)

    def __repr__(self):
        return "Periodic[interval: [{}], {}]".format(self.interval, Hook.__repr__(self))

    def __str__(self):
        return "periodic hook ({} seconds) {} from {}".format(
            self.interval, self.function_name, self.plugin.file_name
        )


class SieveHook(Hook):
    def __init__(self, plugin, sieve_hook):
        """
        :type plugin: Plugin
        :type sieve_hook: cloudbot.util.hook._SieveHook
        """

        self.priority = sieve_hook.kwargs.pop("priority", 100)
        # We don't want to thread sieves by default - this is retaining old behavior for compatibility
        super().__init__("sieve", plugin, sieve_hook)

    def __repr__(self):
        return "Sieve[{}]".format(Hook.__repr__(self))

    def __str__(self):
        return "sieve {} from {}".format(self.function_name, self.plugin.file_name)


class EventHook(Hook):
    """
    :type types: set[cloudbot.event.EventType]
    """

    def __init__(self, plugin, event_hook):
        """
        :type plugin: Plugin
        :type event_hook: cloudbot.util.hook._EventHook
        """
        super().__init__("event", plugin, event_hook)

        self.types = event_hook.types

    def __repr__(self):
        return "Event[types: {}, {}]".format(list(self.types), Hook.__repr__(self))

    def __str__(self):
        return "event {} ({}) from {}".format(
            self.function_name,
            ",".join(str(t) for t in self.types),
            self.plugin.file_name,
        )


class OnStartHook(Hook):
    def __init__(self, plugin, on_start_hook):
        """
        :type plugin: Plugin
        :type on_start_hook: cloudbot.util.hook._On_startHook
        """
        super().__init__("on_start", plugin, on_start_hook)

    def __repr__(self):
        return "On_start[{}]".format(Hook.__repr__(self))

    def __str__(self):
        return "on_start {} from {}".format(self.function_name, self.plugin.file_name)


class OnConnReadyHook(Hook):
    def __init__(self, plugin, on_connection_ready_hook):
        super().__init__("on_connection_ready", plugin, on_connection_ready_hook)

    def __repr__(self):
        return "On_ready[{}]".format(Hook.__repr__(self))

    def __str__(self):
        return "on_connection_readyy {} from {}".format(
            self.function_name, self.plugin.file_name
        )


class OnReadyHook(Hook):
    def __init__(self, plugin, on_ready_hook):
        super().__init__("on_ready", plugin, on_ready_hook)

    def __repr__(self):
        return "On_ready[{}]".format(Hook.__repr__(self))

    def __str__(self):
        return "on_ready {} from {}".format(self.function_name, self.plugin.file_name)


def find_hooks(parent, module):
    """
    :type parent: Plugin
    :type module: object
    :rtype: (list[CommandHook], list[SieveHook], List[EventHook], list[OnStartHook])
    """
    # set the loaded flag
    module._cloudbot_loaded = True
    command = []
    sieve = []
    event = []
    periodic = []
    on_start = []
    on_ready = []
    on_conn_ready = []
    type_lists = {
        "command": command,
        "sieve": sieve,
        "event": event,
        "periodic": periodic,
        "on_start": on_start,
        "on_ready": on_ready,
        "on_connection_ready": on_conn_ready,
    }
    for name, func in module.__dict__.items():
        if hasattr(func, "_cloudbot_hook"):
            # if it has cloudbot hook
            func_hooks = func._cloudbot_hook

            for hook_type, func_hook in func_hooks.items():
                type_lists[hook_type].append(
                    _hook_name_to_plugin[hook_type](parent, func_hook)
                )

            # delete the hook to free memory
            del func._cloudbot_hook

    return command, sieve, event, periodic, on_start, on_ready, on_conn_ready


def find_tables(code):
    """
    :type code: object
    :rtype: list[sqlalchemy.Table]
    """
    tables = []
    for name, obj in code.__dict__.items():
        if isinstance(obj, sqlalchemy.Table) and obj.metadata == database.metadata:
            # if it's a Table, and it's using our metadata, append it to the list
            tables.append(obj)

    return tables


_hook_name_to_plugin = {
    "command": CommandHook,
    "sieve": SieveHook,
    "event": EventHook,
    "periodic": PeriodicHook,
    "on_start": OnStartHook,
    "on_ready": OnReadyHook,
    "on_connection_ready": OnConnReadyHook,
}
