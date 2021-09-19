# Delay checking for typing (TODO: remove when bot runs on python 3.10)
from __future__ import annotations
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .hook2 import Hook
    from .actions import ActionCommand

from .hooklet import Command
import inspect
from functools import wraps


def subcommand(**kwargs):
    def wrap(func):
        if hasattr(func, "__func__"):
            func = func.__func__
        func.__spanky_wrapped = True
        func.__spanky_kwargs = kwargs
        func.__spanky_cmdname = kwargs.get("name", func.__name__)
        return func

    return wrap


def cmd_from(cmd: ComplexCommand, func):
    if "__spanky_wrapped" not in func.__dict__:
        func = subcommand()(func)
    return Command(cmd.hook, func.__spanky_cmdname, func, **func.__spanky_kwargs)


# ComplexCommand is a class, which must be inherited, that groups a set of subcommands under a common command name.
# This might still be a bit buggy!
# SubCommands must be wrapped with the @subcommand decorator, its kwargs being passed to a hidden Command hooklet, and specified in the self.subcommands during init() (this is a technical python limitation, I don't think I can work around it) (TODO: Is there any way to work around it?)
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
        self.help_cmd = None

        # Child-provided init
        self.init()

        # Based on the child-provided init, generate subcommands
        self._gen_commands()

    def init(self):
        raise Exception("init() not defined for Complex Command")

    def _gen_commands(self):
        # Help command that is the default if subcommand is not found
        if not isinstance(self.help_cmd, Command):
            if self.help_cmd == None:

                def help():
                    return (
                        "Invalid subcommand name. This will be a help page someday :)"
                    )

                self.help_cmd = subcommand()(help)
            self.help_cmd = cmd_from(self, self.help_cmd)
            self._sub_commands.append(self.help_cmd)

        for cmd in self.subcommands:
            self._sub_commands.append(cmd_from(self, cmd))

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


__all__ = [subcommand, ComplexCommand]
