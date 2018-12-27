import json
import logging
import re
import threading
import importlib
import time

from spanky.plugin.plugin_manager import PluginManager
from spanky.plugin.event import EventType, TextEvent, TimeEvent, RegexEvent
from spanky.database.db import db_data

logger = logging.getLogger("spanky")

class Bot():
    def __init__(self, input_type):
        with open('bot_config.json') as data_file:
            self.config = json.load(data_file)

        db_path = self.config.get('database', 'sqlite:///cloudbot.db')
        # Open the database first
        self.db = db_data(db_path)

        self.plugin_manager = PluginManager(
            self.config.get("plugin_paths", ""), self, self.db)
        
        try:
            module = importlib.import_module("spanky.inputs.%s" % input_type)
            self.input = module
        except:
            import traceback
            import sys
            print(traceback.format_exc())
            sys.exit(1)

    def on_message_edit(self, before, after):
        """On message edit external hook"""
        cont = self.input.EventMessage(EventType.message, before, after)
        
        self.do_text_event(cont)

    def on_message(self, message):
        """On message external hook"""
        evt = self.input.EventMessage(EventType.message, message)
        
        self.do_text_event(evt)
        
    def do_text_event(self, event):
        """Process a text event"""
        
        # Check if the command starts with .
        if event.msg.text.startswith("."):
            # Get the actual command
            cmd_match = re.split(r'(\W+)', event.msg.text, 2)
            logger.debug("Got command %s" % str(cmd_match))
            command = cmd_match[2].lower()
            
            # Check if it's in the command list
            if command in self.plugin_manager.commands.keys():
                command_hook = self.plugin_manager.commands[command]
                event_text = event.msg.text[len(event.msg.text)+1:]
                text_event = TextEvent(
                    hook=command_hook, 
                    text=event_text,
                    triggered_command=command, 
                    event=event,
                    bot=self)

                # TODO account for these
                thread = threading.Thread(target=self.plugin_manager.launch, args=(text_event,))
                thread.start()
                
        # Regex hooks
        for regex, regex_hook in self.plugin_manager.regex_hooks:
            regex_match = regex.search(event.msg.text)
            if regex_match:
                regex_event = RegexEvent(bot=self, hook=regex_hook, match=regex_match, event=event)
                thread = threading.Thread(target=self.plugin_manager.launch, args=(regex_event,))
                thread.start()
            
    def on_periodic(self):
        for _, plugin in self.plugin_manager.plugins.items():
            for periodic in plugin.periodic:
                if time.time() - periodic.last_time > periodic.interval:
                    periodic.last_time = time.time()
                    t_event = self.input.EventPeriodic()
                    event = TimeEvent(bot=self, hook=periodic, event=t_event)
    
                    # TODO account for these
                    thread = threading.Thread(target=self.plugin_manager.launch, args=(event,))
                    thread.start()
