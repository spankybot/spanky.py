import json
import logging
import re
import threading
import importlib
import time
import asyncio

from spanky.database.db import db_data
from spanky.plugin.permissions import PermissionMgr
from spanky.plugin.hook_logic import OnStartHook
from spanky.hook2 import hook2
from spanky.hook2.event import EventType
from spanky.hook2.hook_manager import HookManager
from spanky.hook2.actions import (
    Action,
    ActionCommand,
    ActionPeriodic,
    ActionEvent,
    ActionOnReady,
)

logger = logging.getLogger("spanky")
logger.setLevel(logging.DEBUG)

audit = logging.getLogger("audit")
audit.setLevel(logging.DEBUG)
# create file handler which logs even debug messages
fh = logging.FileHandler("audit.log")
fh.setLevel(logging.DEBUG)
audit.addHandler(fh)


def print_hook_assocs(hook: hook2.Hook):
    out = ""
    for ch in hook.children:
        out += f'"{hook.hook_id}"-> "{ch.hook_id}"\n{print_hook_assocs(ch)}'
    return out


class Bot:
    def __init__(self, input_type):
        self.user_agent = "spanky.py bot https://github.com/gc-plp/spanky.py"
        self.is_ready = False
        self.loop = asyncio.get_event_loop()
        self.hook2 = hook2.Hook("bot_hook")

        # Open the bot config file
        with open("bot_config.json") as data_file:
            self.config = json.load(data_file)

        db_path = self.config.get("database", "sqlite:///cloudbot.db")
        self.logger = logger

        # Open the database first
        self.db = db_data(db_path)

        # Create the plugin manager instance
        self.hook_manager = HookManager(
            ["spanky/core_plugins"] + self.config.get("plugin_paths", []), self
        )

        self._prefix = self.config.get("command_prefix", ".")

        # Import the backend
        try:
            module = importlib.import_module("spanky.inputs.%s" % input_type)
            self.input = module
        except:
            import traceback
            import sys

            print(traceback.format_exc())
            sys.exit(1)

    async def start(self):
        # Initialize the backend module
        self.backend = self.input.Init(self)
        await self.hook_manager.load()
        await self.backend.do_init()

    async def run_on_ready_work(self):
        for server in self.backend.get_servers():
            await self.dispatch_action(ActionOnReady(self, server))

        # Run on connection ready hooks
        await self.dispatch_action(ActionEvent(self, {}, EventType.on_conn_ready))

    async def ready(self):
        # Initialize per server permissions
        self.server_permissions = {}
        for server in self.backend.get_servers():
            self.server_permissions[server.id] = PermissionMgr(server)

        await self.run_on_ready_work()

        self.is_ready = True

    def get_servers(self):
        return self.backend.get_servers()

    def get_pmgr(self, server_id):
        """
        Get permission manager for a given server ID.
        """

        # Maybe the bot joined a server later
        if server_id not in self.server_permissions:
            server_list = {}

            for server in self.backend.get_servers():
                server_list[server.id] = server

            if server_id in server_list.keys():
                self.server_permissions[server_id] = PermissionMgr(
                    server_list[server_id]
                )

        return self.server_permissions[server_id]

    def get_own_id(self):
        """
        Get bot user ID from backend.
        """
        return self.backend.get_own_id()

    def get_bot_roles_in_server(self, server):
        return self.backend.get_bot_roles_in_server(server)

    def run_in_thread(self, target, args=()):
        thread = threading.Thread(target=target, args=args)
        thread.start()

    async def dispatch_action(self, action: Action):
        await self.hook2.dispatch_action(action)

    # ---------------
    # Server events
    # ---------------
    async def on_server_join(self, server):
        pass

    async def on_server_leave(self, server):
        pass

    # ----------------
    # Message events
    # ----------------

    async def on_message_delete(self, message):
        """On message delete external hook"""
        evt = self.input.EventMessage(EventType.message_del, message, deleted=True)

        await self.do_text_event(evt)

    async def on_bulk_message_delete(self, messages):
        """On message bulk delete external hook"""
        evt = self.input.EventMessage(
            EventType.msg_bulk_del, messages[0], deleted=True, messages=messages
        )

        await self.do_text_event(evt)

    async def on_message_edit(self, before, after):
        """On message edit external hook"""
        evt = self.input.EventMessage(EventType.message_edit, after, before)

        await self.do_text_event(evt)

    async def on_message(self, message):
        """On message external hook"""
        evt = self.input.EventMessage(EventType.message, message)

        await self.do_text_event(evt)

    # ----------------
    # Member events
    # ----------------
    async def on_member_update(self, before, after):
        evt = self.input.EventMember(
            EventType.member_update, member=before, member_after=after
        )
        await self.do_non_text_event(evt)

    async def on_member_join(self, member):
        evt = self.input.EventMember(EventType.join, member)
        await self.do_non_text_event(evt)

    async def on_member_remove(self, member):
        evt = self.input.EventMember(EventType.part, member)
        await self.do_non_text_event(evt)

    async def on_member_ban(self, server, member):
        pass

    async def on_member_unban(self, server, member):
        pass

    # ----------------
    # Reaction events
    # ----------------
    async def on_reaction_add(self, reaction, user):
        evt = self.input.EventReact(
            EventType.reaction_add, user=user, reaction=reaction
        )
        await self.do_non_text_event(evt)

    async def on_reaction_remove(self, reaction, user):
        evt = self.input.EventReact(
            EventType.reaction_remove, user=user, reaction=reaction
        )
        await self.do_non_text_event(evt)

    async def do_non_text_event(self, event):
        # Don't do anything if bot is not connected
        if not self.is_ready:
            return

        await self.dispatch_action(
            ActionEvent(self, event, EventType(event.type.value))
        )

    async def do_text_event(self, event):
        """Process a text event"""
        # Don't do anything if bot is not connected
        if not self.is_ready:
            return

        await self.dispatch_action(
            ActionEvent(self, event, EventType(event.type.value))
        )

        # Let's not
        # Ignore private messages
        # if event.is_pm and event.msg.text.split(maxsplit=1)[0] != ".accept_invite":
        #    return

        # Don't answer to own commands and don't trigger invalid events
        if event.author.bot or not event.do_trigger:
            return

        cmd_text = event.msg.text.lstrip()

        # Check if the command starts with .
        if not (len(cmd_text) > 1 and cmd_text[0] == self._prefix):
            return

        # Get the actual command
        cmd_split = cmd_text[1:].split(maxsplit=1)

        command = cmd_split[0]
        logger.debug("Got command %s" % str(command))
        if len(cmd_split) == 1:
            cmd_split.append("")

        # Hook2
        # if command in self.hook2.all_commands.keys():
        # hooklet = self.hook2.all_commands[command]
        # TODO: Move to middleware and make command-agnostic
        # if event.is_pm and not hooklet.can_pm:
        #    return
        # if not event.is_pm and hooklet.pm_only:
        #    return

        await self.dispatch_action(ActionCommand(self, event, cmd_split[1], command))

        if event.is_pm:
            # Log audit data
            audit.info(
                "[%s][%s][%s] / <%s> %s"
                % (
                    "pm",
                    event.msg.id,
                    "pm",
                    event.author.name
                    + "/"
                    + str(event.author.id)
                    + "/"
                    + event.author.nick,
                    event.text,
                )
            )
        else:
            # Log audit data
            audit.info(
                "[%s][%s][%s] / <%s> %s"
                % (
                    event.server.name,
                    event.msg.id,
                    event.channel.name,
                    event.author.name
                    + "/"
                    + str(event.author.id)
                    + "/"
                    + event.author.nick,
                    event.text,
                )
            )

    def on_periodic(self):
        if not self.is_ready:
            return

        for hooklet in self.hook2.all_periodics.values():
            if time.time() - hooklet.last_time > hooklet.interval:
                hooklet.last_time = time.time()
                action = ActionPeriodic(self, hooklet.hooklet_id)
                self.dispatch_action(action)
