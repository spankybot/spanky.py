import json
import logging
import re
import threading
import importlib
import time
import asyncio

from spanky.plugin.plugin_manager import PluginManager
from spanky.plugin.event import EventType, TextEvent, TimeEvent, RegexEvent, HookEvent, OnReadyEvent, OnConnReadyEvent
from spanky.database.db import db_data
from spanky.plugin.permissions import PermissionMgr
from spanky.plugin.hook_logic import OnStartHook

logger = logging.getLogger("spanky")
logger.setLevel(logging.DEBUG)

audit = logging.getLogger("audit")
audit.setLevel(logging.DEBUG)
# create file handler which logs even debug messages
fh = logging.FileHandler('audit.log')
fh.setLevel(logging.DEBUG)
audit.addHandler(fh)

class Bot():
    def __init__(self, input_type):
        self.user_agent = "spaky.py bot https://github.com/gc-plp/spanky.py"
        self.is_ready = False
        self.loop = asyncio.get_event_loop()

        # Open the bot config file
        with open('bot_config.json') as data_file:
            self.config = json.load(data_file)

        db_path = self.config.get('database', 'sqlite:///cloudbot.db')
        self.logger = logger

        # Open the database first
        self.db = db_data(db_path)

        # Create the plugin manager instance
        self.plugin_manager = PluginManager(
            self.config.get("plugin_paths", ""), self, self.db)

        self._prefix = self.config.get("command_prefix")

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
        await self.backend.do_init()

    def run_on_ready_work(self):
        for server in self.backend.get_servers():
            for on_ready in self.plugin_manager.run_on_ready:
                self.plugin_manager.launch(
                    OnReadyEvent(
                        bot=self,
                        hook=on_ready,
                        permission_mgr=self.get_pmgr(server.id),
                        server=server))

        # Run on connection ready hooks
        for on_conn_ready in self.plugin_manager.run_on_conn_ready:
            self.plugin_manager.launch(
                    OnConnReadyEvent(
                        bot=self,
                        hook=on_conn_ready))

    def ready(self):
        # Initialize per server permissions
        self.server_permissions = {}
        for server in self.backend.get_servers():
            self.server_permissions[server.id] = PermissionMgr(server)

        self.run_on_ready_work()

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
                self.server_permissions[server_id] = \
                    PermissionMgr(server_list[server_id])

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

# ---------------
# Server events
# ---------------
    def on_server_join(self, server):
        pass

    def on_server_leave(self, server):
        pass

# ----------------
# Message events
# ----------------

    def on_message_delete(self, message):
        """On message delete external hook"""
        evt = self.input.EventMessage(EventType.message_del, message, deleted=True)

        self.do_text_event(evt)

    def on_bulk_message_delete(self, messages):
        """On message bulk delete external hook"""
        evt = self.input.EventMessage(EventType.msg_bulk_del, messages[0], deleted=True, messages=messages)

        self.do_text_event(evt)

    def on_message_edit(self, before, after):
        """On message edit external hook"""
        evt = self.input.EventMessage(EventType.message_edit, after, before)

        self.do_text_event(evt)

    def on_message(self, message):
        """On message external hook"""
        evt = self.input.EventMessage(EventType.message, message)

        self.do_text_event(evt)

# ----------------
# Member events
# ----------------
    def on_member_update(self, before, after):
        evt = self.input.EventMember(EventType.member_update, member=before, member_after=after)
        self.do_non_text_event(evt)

    def on_member_join(self, member):
        evt = self.input.EventMember(EventType.join, member)
        self.do_non_text_event(evt)

    def on_member_remove(self, member):
        evt = self.input.EventMember(EventType.part, member)
        self.do_non_text_event(evt)

    def on_member_ban(self, server, member):
        pass

    def on_member_unban(self, server, member):
        pass

# ----------------
# Reaction events
# ----------------
    def on_reaction_add(self, reaction, user):
        evt = self.input.EventReact(EventType.reaction_add, user=user, reaction=reaction)
        self.do_non_text_event(evt)

    def on_reaction_remove(self, reaction, user):
        evt = self.input.EventReact(EventType.reaction_remove, user=user, reaction=reaction)
        self.do_non_text_event(evt)


    def run_type_events(self, event):
        # Raw hooks

        pmgr = None
        # Handle PMs
        if hasattr(event, "server"):
            pmgr = self.get_pmgr(event.server.id)

        for raw_hook in self.plugin_manager.catch_all_triggers:
            self.run_in_thread(self.plugin_manager.launch, (
                HookEvent(
                    bot=self,
                    hook=raw_hook,
                    event=event,
                    permission_mgr=pmgr),))

        # Event hooks
        if event.type in self.plugin_manager.event_type_hooks:
            for event_hook in self.plugin_manager.event_type_hooks[event.type]:
                self.run_in_thread(
                    self.plugin_manager.launch, (
                        HookEvent(bot=self,
                                  hook=event_hook,
                                  event=event,
                                  permission_mgr=pmgr),))

    def do_non_text_event(self, event):
        if not self.is_ready:
            return

        self.run_type_events(event)

    def do_text_event(self, event):
        """Process a text event"""
        # Don't do anything if bot is not connected
        if not self.is_ready:
            return

        # Let's not
        # Ignore private messages
        #if event.is_pm and event.msg.text.split(maxsplit=1)[0] != ".accept_invite":
        #    return

        self.run_type_events(event)

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

        # Check if it's in the command list
        if command in self.plugin_manager.commands.keys():
            hook = self.plugin_manager.commands[command]

            # Test if we can actually send a PM with the command
            if event.is_pm and not hook.can_pm:
                return
            if not event.is_pm and hook.pm_only:
                return

            if len(cmd_split) > 1:
                event_text = cmd_split[1]
            else:
                event_text = ""

            pmgr = None
            # Handle PMs
            if hasattr(event, "server"):
                pmgr = self.get_pmgr(event.server.id)

            text_event = TextEvent(
                hook=hook,
                text=event_text,
                triggered_command=command,
                event=event,
                bot=self,
                permission_mgr=pmgr)

            if event.is_pm:
                # Log audit data
                audit.info("[%s][%s][%s] / <%s> %s" % (
                    "pm",
                    event.msg.id,
                    "pm",
                    event.author.name + "/" + str(event.author.id) + "/" + event.author.nick,
                    event.text))
            else:
                # Log audit data
                audit.info("[%s][%s][%s] / <%s> %s" % (
                    event.server.name,
                    event.msg.id,
                    event.channel.name,
                    event.author.name + "/" + str(event.author.id) + "/" + event.author.nick,
                    event.text))
            self.run_in_thread(target=self.plugin_manager.launch, args=(text_event,))

        # Regex hooks
        for regex, regex_hook in self.plugin_manager.regex_hooks:
            regex_match = regex.search(event.msg.text)
            if regex_match:
                regex_event = RegexEvent(bot=self, hook=regex_hook, match=regex_match, event=event)
                thread = threading.Thread(target=self.plugin_manager.launch, args=(regex_event,))
                thread.start()

    def on_periodic(self):
        if not self.is_ready:
            return

        for _, plugin in self.plugin_manager.plugins.items():
            for periodic in plugin.periodic:
                if time.time() - periodic.last_time > periodic.interval:
                    periodic.last_time = time.time()
                    t_event = self.input.EventPeriodic()
                    event = TimeEvent(bot=self, hook=periodic, event=t_event)

                    # TODO account for these
                    thread = threading.Thread(target=self.plugin_manager.launch, args=(event,))
                    thread.start()
