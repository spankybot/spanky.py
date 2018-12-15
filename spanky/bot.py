import json

from spanky.plugin.plugin_manager import PluginManager
from spanky.plugin.event import EventContainer, EventType
from spanky.database.db import db_data

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
        pass

    def on_message(self, message):
        return EventContainer(
            EventType.message,
            {
                "message": message
            })
