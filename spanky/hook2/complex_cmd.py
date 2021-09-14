# Delay checking for typing (TODO: remove when bot runs on python 3.10)
from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from .hook2 import Hook
    from .actions import ActionCommand

from .hooklet import Command
import copy

def command(**kwargs):
    def wrap(func):
        func.__spanky_wrapped = True
        func.__spanky_kwargs = kwargs
        return func
    return wrap

class ComplexCommand(Command):
    def __init__(self, hook: Hook, name: str, **kwargs):
        super().__init__(hook, name, self.run_cmd, **kwargs)
        self.subcommands: list[Any] = []
        self._sub_commands: list[Command] = []

        # Child-provided init
        self.init()

        # Based on the child-provided init, generate subcommands
        self._gen_commands()

    def init(self):
        raise Exception('init() not defined for Complex Command')

    def _gen_commands(self):
        for cmd in self.subcommands:
            if '__spanky_wrapped' not in cmd:
                raise Exception('subcommand not wrapped')
            self._sub_commands.append(Command(self.hook, cmd.__name__, cmd, **cmd.__spanky_kwargs))

    def get_cmd(self, action: ActionCommand) -> tuple[Command, ActionCommand]:
        # TODO: Get cmd and cmdname
        cmd = Command()
        cmdname = ''

        act = copy.copy(action)
        act.text = act.text.removeprefix(cmdname + ' ')
        return cmd, act

    def run_cmd(self, action: ActionCommand):
        # Aici ne folosim de self._sub_commands pentru a face handle la subcommands 
        pass
