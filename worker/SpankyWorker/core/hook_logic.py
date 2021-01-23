import inspect
import logging

from ..utils import time_utils as tutils
from .hook_parameters import extract_params


logger = logging.getLogger("spanky")


class Hook:
    """
    Each hook is specific to one function. This class is never used by itself, rather extended.
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
        self.name = self.function.__name__

        # Get required args
        self.required_args = inspect.getargspec(self.function)[0]
        if self.required_args is None:
            self.required_args = []

        # don't process args starting with "_"
        self.required_args = [
            arg for arg in self.required_args if not arg.startswith("_")
        ]

        # Parse hook parameters
        self.permissions = func_hook.kwargs.pop("permissions", [])
        self.format = func_hook.kwargs.pop("format", None)
        self.server_id = func_hook.kwargs.pop("server_id", None)
        self.server_id = self.server_id

        # If storage is saved per server or it's unique
        self.unique_storage = func_hook.kwargs.pop("unique_storage", False)

        # Mark if the plugin needs storage or storage_loc
        self.needs_storage = False
        if (
            "storage" in self.required_args
            or "storage_loc" in self.required_args
        ):
            self.needs_storage = True

        # Mark if cmd_args is requested
        self.given_cmd_params = func_hook.kwargs.pop("params", None)

        # Mark if cmd_args are strict
        self.cmd_params_strict = func_hook.kwargs.pop("params_strict", False)

        # Extract processed parameter list
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
        """
        Check if the hook has a server ID or list of server IDs specified
        """
        # If no server id specified, it can run
        if not self.server_id:
            return True

        if type(self.server_id) == str:
            return self.server_id == sid
        elif type(self.server_id) == list:
            return sid in self.server_id

        return False

    @property
    def description(self):
        return "{}:{}".format(self.plugin.name, self.name)

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
        super().__init__("command", plugin, cmd_hook)

    def __repr__(self):
        return "Command[name: {}, {}]".format(self.name, Hook.__repr__(self))

    def __str__(self):
        return "command {} from {}".format(
            "/".join(self.name), self.plugin.file_name
        )


class RegexHook(Hook):
    """
    :type regexes: set[re.__Regex]
    """

    def __init__(self, plugin, regex_hook):
        """
        :type plugin: Plugin
        :type regex_hook: cloudbot.util.hook._RegexHook
        """
        self.regexes = regex_hook.regexes

        super().__init__("regex", plugin, regex_hook)

    def __repr__(self):
        return "Regex[regexes: [{}], {}]".format(
            ", ".join(regex.pattern for regex in self.regexes),
            Hook.__repr__(self),
        )

    def __str__(self):
        return "regex {} from {}".format(self.name, self.plugin.file_name)


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
        self.last_time = tutils.tnow()

        super().__init__("periodic", plugin, periodic_hook)

    def __repr__(self):
        return "Periodic[interval: [{}], {}]".format(
            self.interval, Hook.__repr__(self)
        )

    def __str__(self):
        return "periodic hook ({} seconds) {} from {}".format(
            self.interval, self.name, self.plugin.file_name
        )


class RawHook(Hook):
    """
    :type triggers: set[str]
    """

    def __init__(self, plugin, msg_raw_hook):
        """
        :type plugin: Plugin
        :type msg_raw_hook: cloudbot.util.hook._RawHook
        """
        super().__init__("msg_raw", plugin, msg_raw_hook)

        self.triggers = msg_raw_hook.triggers

    def is_catch_all(self):
        return "*" in self.triggers

    def __repr__(self):
        return "Raw[triggers: {}, {}]".format(
            list(self.triggers), Hook.__repr__(self)
        )

    def __str__(self):
        return "irc raw {} ({}) from {}".format(
            self.name, ",".join(self.triggers), self.plugin.file_name
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
        return "sieve {} from {}".format(self.name, self.plugin.file_name)


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
        return "Event[types: {}, {}]".format(
            list(self.types), Hook.__repr__(self)
        )

    def __str__(self):
        return "event {} ({}) from {}".format(
            self.name,
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
        return "on_start {} from {}".format(self.name, self.plugin.file_name)


class OnReadyHook(Hook):
    def __init__(self, plugin, on_ready_hook):
        super().__init__("on_ready", plugin, on_ready_hook)

    def __repr__(self):
        return "On_ready[{}]".format(Hook.__repr__(self))

    def __str__(self):
        return "on_ready {} from {}".format(self.name, self.plugin.file_name)


def find_hooks(parent, module):
    """
    :type parent: Plugin
    :type module: object
    :rtype: (list[CommandHook], list[RegexHook], list[RawHook], list[SieveHook], List[EventHook], list[OnStartHook])
    """
    # set the loaded flag
    module._cloudbot_loaded = True
    command = []
    regex = []
    raw = []
    sieve = []
    event = []
    periodic = []
    on_start = []
    on_ready = []

    type_lists = {
        "command": command,
        "regex": regex,
        "msg_raw": raw,
        "sieve": sieve,
        "event": event,
        "periodic": periodic,
        "on_start": on_start,
        "on_ready": on_ready,
    }

    for _, func in module.__dict__.items():
        if hasattr(func, "_bot_hook"):
            # mark that it is a bot hook
            func_hooks = func._bot_hook

            for hook_type, func_hook in func_hooks.items():
                type_lists[hook_type].append(
                    _hook_name_to_plugin[hook_type](parent, func_hook)
                )

            # delete the hook to free memory
            del func._bot_hook

    return command, regex, raw, sieve, event, periodic, on_start, on_ready


_hook_name_to_plugin = {
    "command": CommandHook,
    "regex": RegexHook,
    "msg_raw": RawHook,
    "sieve": SieveHook,
    "event": EventHook,
    "periodic": PeriodicHook,
    "on_start": OnStartHook,
    "on_ready": OnReadyHook,
}
