import json
import logging
import re
import threading

from spanky.plugin.plugin_manager import PluginManager
from spanky.plugin.event import EventContainer, EventType, TextEvent
from spanky.database.db import db_data

logger = logging.getLogger("spanky")

class Bot():
    def __init__(self):
        with open('bot_config.json') as data_file:
            self.config = json.load(data_file)

        db_path = self.config.get('database', 'sqlite:///cloudbot.db')
        # Open the database first
        self.db = db_data(db_path)

        self.plugin_manager = PluginManager(
            self.config.get("plugin_paths", ""), self.db)

    def on_message_edit(self, before, after):
        """On message edit external hook"""
        pass

    def on_message(self, message):
        """On message external hook"""
        cont = EventContainer(
            EventType.message,
            {
                "message": message,
                "text": message.text
            })
        
        self.do_text_event(cont)
        
    def do_text_event(self, event):
        """Process a text event"""
        
        # Check if the command starts with .
        if event.text.startswith("."):
            # Get the actual command
            cmd_match = re.split(r'(\W+)', event.text, 2)
            logger.debug("Got command %s" % str(cmd_match))
            command = cmd_match[2].lower()
            
            # Check if it's in the command list
            if command in self.plugin_manager.commands.keys():
                logger.debug("Command is valid")
                
                command_hook = self.plugin_manager.commands[command]
                event_text = event.text[len(event.text)+1:]
                text_event = TextEvent(
                    hook=command_hook, 
                    text=event_text,
                    triggered_command=command, 
                    event=event,
                    bot=self)

                # TODO account for these
                thread = threading.Thread(target=self.plugin_manager.launch, args=(text_event,))
                thread.start()