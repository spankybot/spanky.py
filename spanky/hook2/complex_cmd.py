# Delay checking for typing (TODO: remove when bot runs on python 3.10)
from __future__ import annotations
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .hook2 import Hook
    from .actions import ActionCommand

from .hooklet import Command
import inspect
from functools import wraps


def default_help():
    return "Invalid subcommand name. This will be a help page someday :)"


# ComplexCommand is a class, which must be inherited, that groups a set of subcommands under a common command name.
# This might still be a bit buggy!
# An effective example will be located in spanky/core_plugins/perms.py
# Please note that middleware is parsed separately for the command and the subcommand:
# For example, if the ComplexCommand class has a permissions=["admin"] attribute, the command will be denied to non-admins.
# If the subcommand has a permissions=["bot_owner"] attribute, the admin must also be a bot_owner.
# Effectively, the hooklet attributes' results should be AND-ed for the filtering in middleware
# TODO: I think this documentation (and maybe the class's usage) is confusing, it should be cleaned up.
class ComplexCommand(Command):
    def __init__(self, hook: Hook, name: str, **kwargs):
        super().__init__(hook, name, self.run_cmd, **kwargs)
        self.subcommands: list[Any] = []
        self._sub_commands: list[Command] = []

        self.help_cmd = Command(self.hook, "help", default_help)

        self.hook.add_command(self.name, self)

    def subcommand(self, **kwargs):
        def make_cmd(func):
            self._sub_commands.append(
                Command(self.hook, kwargs.get("name", func.__name__), func, **kwargs)
            )
            return func

        return make_cmd

    def help(self, **kwargs):
        def make_cmd(func):
            cmd = Command(self.hook, "help", func, **kwargs)
            self._sub_commands.append(cmd)
            self.help_cmd = cmd
            return func

        return make_cmd

    def get_cmd(self, action: ActionCommand) -> tuple[Command, ActionCommand]:
        cmd_split = action.text.split(maxsplit=1)

        if len(cmd_split) == 0:
            return self.help_cmd, action
        cmdname = cmd_split[0]
        if len(cmd_split) == 1:
            cmd_split.append("")

        for cmd in self._sub_commands:
            if cmd.name == cmdname:
                act = action.copy()
                act.text = cmd_split[1]
                print(cmd.name)
                return cmd, act

        return self.help_cmd, action

    async def run_cmd(self, action: ActionCommand):
        cmd, action = self.get_cmd(action)
        print(cmd.name)
        await cmd.handle(action)
