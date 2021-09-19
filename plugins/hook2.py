from spanky.hook2 import hook2
import time
from spanky.hook2.event import EventType
from spanky.hook2.complex_cmd import ComplexCommand, subcommand

hk2 = hook2.Hook(f"plugins_hook2_{int(time.time())}")

print(hk2)


class TestCmd(ComplexCommand):
    def init(self):
        self.subcommands = [self.subcmd, self.subcmd2, self.testtt_cmd]
        # self.help_cmd = self.help

    @subcommand()
    def subcmd(self):
        return "Cf"

    @subcommand()
    def subcmd2(self):
        return "Subcomandă"

    @subcommand()
    def testtt_cmd(self):
        print(self)
        return "bruh"

    @subcommand()
    def help(self):
        return "Help suprascris"


@hk2.command()
def test_hook2(reply):
    reply("COMMAND EXECUTED WITH HOOK2")


@hk2.event(EventType.on_start)
def start_test(hook):
    hk2.add_command("test_cmd", TestCmd(hook, "test_cmd"))
    print(f"Started beeeyoootch.")
