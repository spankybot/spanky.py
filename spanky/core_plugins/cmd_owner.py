from spanky.hook2 import (
    Hook,
    Command,
    ComplexCommand,
    ActionCommand,
    EventType,
    MiddlewareResult,
)

# TODO: storage might be unsafe?
hook = Hook("cmd_owner_hook", storage_name="plugins_admin.json")


@hook.global_middleware(priority=15)
def check_cmd_owner(action: ActionCommand, hooklet: Command):
    # If not already admin, we should add that he is "technically" an admin for the owner.
    cmd = CmdPerms(
        hooklet.hook.server_storage(action.server_id), action.triggered_command
    )
    print(action.context)
    if "admin" not in action.context["perms"]["creds"]:

        allowed_roles = set(cmd.owners)
        user_roles = set([i.id for i in action.author.roles])
        if user_roles & allowed_roles:
            action.context["perms"]["creds"].append("admin")


@hook.global_middleware(priority=20)
def check_chgroups(action: ActionCommand, hooklet: Command):
    storage = hooklet.hook.server_storage(action.server_id)
    cmd = CmdPerms(storage, action.triggered_command)
    if cmd.customized:
        if cmd.unrestricted:
            return MiddlewareResult.CONTINUE
        if len(cmd.fchannel_ids) > 0 and action.channel.id in cmd.fchannel_ids:
            action.message.delete_message()
            return (
                MiddlewareResult.DENY,
                "Command can't be used in "
                + ", ".join(action._raw.id_to_chan(i) for i in cmd.fchannel_ids),
            )
        if len(cmd.channel_ids) > 0 and action.channel.id not in cmd.channel_ids:
            action.message.delete_message()
            return (
                MiddlewareResult.DENY,
                "Command can't be here. Try using it in "
                + ", ".join(action._raw.id_to_chan(i) for i in cmd.channel_ids),
            )
    elif (
        storage["default_bot_chan"] and action.channel.id != storage["default_bot_chan"]
    ):
        action.message.delete_message()
        return (
            MiddlewareResult.DENY,
            "Command can only be used in "
            + action._raw.id_to_chan(storage["default_bot_chan"]),
        )


class CmdPerms:
    def __init__(self, storage, cmd: str):
        self.storage = storage
        self.cmd: str = cmd

        self.customized: bool = False
        self.unrestricted: bool = False
        self.owners: list[str] = []
        self.chgroups: list[str] = []
        self.channel_ids: list[str] = []
        self.fchgroups: list[str] = []
        self.fchannel_ids: list[str] = []

        if not storage["commands"]:
            return

        if cmd not in storage["commands"]:
            return

        if "owner" in storage["commands"][cmd].keys():
            self.owners.extend(storage["commands"][cmd]["owner"])
            if len(self.owners) > 0:
                self.customized = True

        if "groups" in storage["commands"][cmd].keys():
            self.chgroups.extend(storage["commands"][cmd]["groups"])

            for chgroup in storage["commands"][cmd]["groups"]:
                if "channels" in storage["chgroups"][chgroup].keys():
                    self.channel_ids.extend(storage["chgroups"][chgroup]["channels"])
            if len(self.channel_ids) > 0:
                self.customized = True

        if "fgroups" in storage["commands"][cmd].keys():
            self.fchgroups.extend(storage["commands"][cmd]["fgroups"])

            for chgroup in storage["commands"][cmd]["fgroups"]:
                self.fchannel_ids.extend(storage["chgroups"][chgroup]["channels"])
            if len(self.fchannel_ids) > 0:
                self.customized = True

        if (
            "unrestricted" in storage["commands"][cmd].keys()
            and storage["commands"][cmd]["unrestricted"] != False
        ):
            self.unrestricted = True

    def save(self):
        self.storage["commands"][self.cmd]["owner"] = self.owners
        self.storage["commands"][self.cmd]["unrestricted"] = self.unrestricted
        self.storage["commands"][self.cmd]["groups"] = self.chgroups
        self.storage["commands"][self.cmd]["fgroups"] = self.fchgroups

        self.storage.sync()


"""
class Chgroups(ComplexCommand):
    def init(self):
        self.subcommands = [self.create, self.list, self.remove]
        self.help_cmd = self.help 

    @subcommand()
    def create(self, storage, text):
        if len(text.split()) > 1:
            return "Invalid format"
        if "chgroups" not in storage:
            storage["chgroups"] = {}
            storage.sync()
        if text in storage["chgroups"].keys():
            return "Channel group already exists!"
        storage["chgroups"][text] = {}
        storage.sync()
        return "Channel group created"

    @subcommand()
    def list(self, storage):
        if "chgroups" not in storage:
            storage["chgroups"] = {}
        if len(storage["chgroups"].keys()) == 0:
            return "No channel groups created"
        return ", ".join(storage["chgroups"].keys())

    @subcommand()
    def remove(self, storage):
        return "TODO"

    @subcommand()
    def help(self):
        return "Usage: .chgroups <create|list|remove> <chgroup name>"


class ChgroupChans(ComplexCommand):
    def init(self):
        self.subcommands = []
        self.help_cmd = None


class FChgroups(ComplexCommand):
    def init(self):
        self.subcommands = []
        self.help_cmd = None


class CmdOwner(ComplexCommand):
    def init(self):
        self.subcommands = []
        self.help_cmd = None


class UnrestrictedCmd(ComplexCommand):
    def init(self):
        self.subcommands = [self.make, self.check, self.restore]
        self.help_cmd = self.help

    @subcommand()
    def make(self, text, storage):
        if len(text.split()) > 1:
            return "Invalid format"
        cmd = CmdPerms(storage, text)
        if cmd.unrestricted:
            return "Command already unrestricted!"
        cmd.unrestricted = True
        cmd.save()
        return "Command unrestricted."

    @subcommand()
    def check(self, text, storage):
        if len(text.split()) > 1:
            return "Invalid format"
        cmd = CmdPerms(storage, text)
        if cmd.unrestricted:
            return "Command is unrestricted"
        if cmd.customized:
            return "Command is restricted, but not customized."
        return "Command is restricted"

    @subcommand()
    def restore(self, text, storage):
        if len(text.split()) > 1:
            return "Invalid format"
        cmd = CmdPerms(storage, text)
        if not cmd.unrestricted:
            return "Command already restricted!"
        cmd.unrestricted = False
        cmd.save()
        return "Command restricted."

    @subcommand()
    def help(self):
        return "Usage: .unrestricted <make|check|restore> <cmd_name>"


@hook.event(EventType.on_start)
def load_complex_cmds():
    Chgroups.to_hook("chgroups", hook, permissions="admin")
    ChgroupChans.to_hook("chgroup_chans", hook, permissions="admin")
    FChgroups.to_hook("fchgroups", hook, permissions="admin")
    CmdOwner.to_hook("cmd_owner", hook, permissions="admin")
    UnrestrictedCmd.to_hook("unrestricted", hook, permissions="admin")
"""
