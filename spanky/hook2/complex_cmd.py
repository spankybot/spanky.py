# Delay checking for typing (TODO: remove when bot runs on python 3.11)
from __future__ import annotations
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .hook2 import Hook
    from .actions import ActionCommand

from .hooklet import Command
import inspect
from functools import wraps


# ComplexCommand is a hooklet that groups a set of subcommands under a common command name.
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
        self._sub_commands: list[Command] = []

        self._help_cmd = Command(self.hook, "help", self.__default_help_func)

        self.help_prefix = self.args.get("help_prefix", ".")

        if self.args.get("auto_add", True):
            self.add_to_hook(hook)

    def add_to_hook(self, hook: Hook):
        hook.add_command(self)

    def __default_help_func(self, send_embed):
        send_embed(self.name, "**Usage:**\n" + self.get_doc())

    def get_doc(self):
        text = f"Command usage: `{self.help_prefix}{self.name} <subcommand>`\n"
        text += "Available subcommands:\n"
        cmds = 0
        for subcmd in self._sub_commands:
            if subcmd.name == "help":
                continue
            cmds += 1
            if isinstance(subcmd, ComplexCommand):
                text += f"- `{subcmd.name} <subcommand>`: Available subcommands:\n{subcmd.get_suborder_doc()}"
            else:
                text += f"- `{subcmd.name}`: {subcmd.get_doc()}\n"
        if cmds == 0:
            text += "- No available subcommands"
        return text

    def get_suborder_doc(self):
        cmds = 0
        text = ""
        for subcmd in self._sub_commands:
            if subcmd.name == "help":
                continue

            if isinstance(subcmd, ComplexCommand):
                text += (
                    f"> - `{subcmd.name} <subcommand>`:\n{subcmd.get_suborder_doc()}"
                )
            else:
                text += f"> - `{subcmd.name}`: {subcmd.get_doc()}\n"
            cmds += 1
        if cmds == 0:
            return "> No available subcommands\n"
        return text

    def func_name(self, func):
        return func.__name__.removeprefix(self.name + "_")

    def subcommand(self, **kwargs):
        def make_cmd(func):
            self._sub_commands.append(
                Command(self.hook, kwargs.get("name", self.func_name(func)), func, **kwargs)
            )
            return func

        return make_cmd

    def help_cmd(self, **kwargs):
        def make_cmd(func):
            cmd = Command(self.hook, "help", func, **kwargs)
            self._sub_commands.append(cmd)
            self._help_cmd = cmd
            return func

        return make_cmd

    def complex_subcommand(self, name: str, **kwargs) -> ComplexCommand:
        kwargs["auto_add"] = False
        kwargs["help_prefix"] = self.help_prefix + self.name + " "
        cmd = ComplexCommand(self.hook, name, **kwargs)
        self._sub_commands.append(cmd)
        return cmd

    def get_cmd(self, action: ActionCommand) -> tuple[Command, ActionCommand]:
        cmd_split = action.text.split(maxsplit=1)

        if len(cmd_split) == 0:
            return self._help_cmd, action
        cmdname = cmd_split[0]
        if len(cmd_split) == 1:
            cmd_split.append("")

        for cmd in self._sub_commands:
            if cmd.name == cmdname:
                act = action.copy()
                act.text = cmd_split[1]
                return cmd, act

        return self._help_cmd, action

    async def run_cmd(self, action: ActionCommand):
        cmd, action = self.get_cmd(action)
        print(cmd.name)
        await cmd.handle(action)

    def get_subcommands(self) -> list:
        return self._sub_commands