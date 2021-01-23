import asyncio
import json
import time

from .manager import PluginManager
from .rpc_client import RPCClient
from SpankyCommon.event import EventType
from SpankyCommon.utils import bot_utils as butils
from . import client as bclient


class PythonWorker:
    def __init__(self, client=None):
        # Open the bot config file
        with open("bot_config.json") as data_file:
            self.config = json.load(data_file)

        # Create the client
        given_client = client
        if not client:
            given_client = RPCClient(self.config["server"])

        bclient.set_server_comm(given_client)
        self._is_ready = False

        self.discord_id = None

    def connect(self):
        # Create the plugin manager
        self.plugin_manager = PluginManager(
            self.config.get("plugin_paths", ""), self
        )

        # Connect to the server
        self.my_id = bclient.CGeneric.connect("testplm")

        # Inform the server about our command list
        self.cmd_list = bclient.CGeneric.set_command_list(
            self.my_id, self.plugin_manager.commands.keys()
        )

    def run_on_ready_work(self):
        """
        Runs the work to be done when on ready is received
        """
        # Get discord bot ID
        self.discord_id = bclient.CGeneric.get_bot_id()

        if self._is_ready:
            raise ValueError("Manager already marked as ready")

        self._is_ready = True
        self.plugin_manager.launch_hooks_by_event(EventType.on_ready)

        butils.run_in_thread(self.timer_loop, args=(1,))

    def run(self):
        while True:
            try:
                for evt, payload in bclient.CGeneric.get_event(self.my_id, []):
                    # Handle the payload type
                    if evt == EventType.message:
                        self.handle_message(payload)

                    elif evt == EventType.on_ready:
                        self.run_on_ready_work()
            except:
                import traceback

                traceback.print_exc()
            time.sleep(0.01)

    def handle_message(self, message):
        if not message.content:
            return

        if message.content[0] != ";":
            return

        cmd_split = message.content[1:].split(maxsplit=1)
        command = cmd_split[0]

        # Check if it's in the command list
        if command in self.plugin_manager.commands.keys():
            hook = self.plugin_manager.commands[command]

            if len(cmd_split) > 1:
                event_text = cmd_split[1]
            else:
                event_text = ""

            # Run the command through the plugin manager
            butils.run_in_thread(
                self.plugin_manager.launch_command,
                args=(hook, message, event_text),
            )

    def timer_loop(self, interval):
        while True:
            time.sleep(interval)
            try:
                self.plugin_manager.launch_hooks_by_event(EventType.timer_event)
            except:
                import traceback
                traceback.print_exc()