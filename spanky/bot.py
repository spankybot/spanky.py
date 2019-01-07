import json
import logging
import re
import threading
import importlib
import time
import asyncio

from spanky.plugin.plugin_manager import PluginManager
from spanky.plugin.event import EventType, TextEvent, TimeEvent, RegexEvent, HookEvent, OnReadyEvent
from spanky.database.db import db_data
from spanky.plugin.permissions import PermissionMgr
from spanky.plugin.hook_logic import OnStartHook

logger = logging.getLogger("spanky")

audit = logging.getLogger("audit")
audit.setLevel(logging.DEBUG)
# create file handler which logs even debug messages
fh = logging.FileHandler('audit.log')
fh.setLevel(logging.DEBUG)
audit.addHandler(fh)

class Bot():
    def __init__(self, input_type):
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
                self.run_in_thread(self.plugin_manager.launch, (
                    OnReadyEvent(
                        bot=self, 
                        hook=on_ready, 
                        permission_mgr=self.get_pmgr(server.id),
                        server=server),))
    
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
            if server_id in self.backend.get_servers():
                self.server_permissions[server_id] = \
                    PermissionMgr(self.backend.get_servers()[server_id])
                
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
        
# ---------------- 
# Message events   
# ---------------- 

    def on_message_delete(self, message):
        """On message edit external hook"""
        evt = self.input.EventMessage(EventType.message_del, message, deleted=True)
        
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
        
        self.do_user_event(evt)
        
    def run_type_events(self, event):
        # Raw hooks
        for raw_hook in self.plugin_manager.catch_all_triggers:
            self.run_in_thread(self.plugin_manager.launch, (
                HookEvent(
                    bot=self, 
                    hook=raw_hook, 
                    event=event, 
                    permission_mgr=self.get_pmgr(event.server.id)),))
        
        # Event hooks
        if event.type in self.plugin_manager.event_type_hooks:
            for event_hook in self.plugin_manager.event_type_hooks[event.type]:
                self.run_in_thread(
                    self.plugin_manager.launch, (
                        HookEvent(bot=self, 
                                  hook=event_hook, 
                                  event=event,
                                  permission_mgr=self.get_pmgr(event.server.id)),))

    def do_user_event(self, event):
        if not self.is_ready:
            return
        
        self.run_type_events(event)
        
    def do_text_event(self, event):
        """Process a text event"""
        if not self.is_ready:
            return
        
        if event.is_pm:
            return
        
        self.run_type_events(event)
        
        if event.author.bot:
            return
        
        # Check if the command starts with .
        if event.do_trigger and event.msg.text.startswith("."):
            # Get the actual command
            cmd_match = re.split(r'(\W+)', event.msg.text, 2)
            logger.debug("Got command %s" % str(cmd_match))
            command = cmd_match[2].lower()
            
            # Check if it's in the command list
            if command in self.plugin_manager.commands.keys():
                hook = self.plugin_manager.commands[command]
            
                event_text = event.msg.text[len(command)+2:].strip()
                
                text_event = TextEvent(
                    hook=hook,
                    text=event_text,
                    triggered_command=command, 
                    event=event,
                    bot=self,
                    permission_mgr=self.get_pmgr(event.server.id))
                
                # Log audit data
                audit.info("[%s][%s][%s] / <%s> %s" % (
                    event.server.name, 
                    event.msg.id, 
                    event.channel.name, 
                    event.author.name + "/" + event.author.id + "/" + event.author.nick,
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
