import asyncio

import json
import threading

from common.event import EventType

from core.event import TextEvent, OnReadyEvent
from core.manager import PluginManager
from core.permissions import PermissionMgr

from database.db import db_data

from rpc_client import RPCClient


class PythonWorker():
    def __init__(self):
        # Open the bot config file
        with open('bot_config.json') as data_file:
            self.config = json.load(data_file)

        # Open the database first
        self.db = db_data(self.config.get('database', 'sqlite:///cloudbot.db'))

        # Create the client
        self.client = RPCClient(self.config['server'], "testplm")

        # Initialize server permissions
        self.server_permissions = {}

    async def connect(self):
        # Create the plugin manager
        self.plugin_manager = PluginManager(
            self.config.get("plugin_paths", ""), self, self.db)

        # Connect to the server
        await self.client.connect()

        # Inform the server about our command list
        self.cmd_list = self.client.set_command_list(
            self.plugin_manager.commands.keys())

    async def get_pmgr(self, server_id):
        """
        Get permission manager for a given server ID.
        """

        # Maybe the bot joined a server later
        if server_id not in self.server_permissions.keys():
            # Get the servers
            servers = await self.client.get_servers()

            for server in servers:
                if server.id not in self.server_permissions.keys():
                    self.server_permissions[server_id] = \
                        PermissionMgr(server)

        if server_id not in self.server_permissions.keys():
            raise ValueError(
                f"Server ID {server_id} is not a connected server")

        return self.server_permissions[server_id]

    async def run_on_ready_work(self):
        """
        Runs the work to be done when on ready is received
        """
        # Get the servers
        servers = await self.client.get_servers()

        for server in servers:
            for on_ready in self.plugin_manager.run_on_ready:
                self.plugin_manager.launch(
                    OnReadyEvent(
                        bot=self,
                        hook=on_ready,
                        permission_mgr=await self.get_pmgr(server.id),
                        server=server))

    async def run(self):
        while True:
            evt, payload = await self.client.get_event()

            if evt == EventType.message:
                await self.handle_message(payload)

            elif evt == EventType.on_ready:
                await self.run_on_ready_work()

    async def handle_message(self, message):
        if message.content[0] != ".":
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

            text_event = TextEvent(
                hook=hook,
                text=event_text,
                triggered_command=command,
                event=message,
                bot=self,
                permission_mgr=await self.get_pmgr(message.guild_id),
                channel_id=message.channel_id)

            self.run_in_thread(
                target=self.plugin_manager.launch, args=(text_event,))

    def run_in_thread(self, target, args=()):
        thread = threading.Thread(target=target, args=args)
        thread.start()


loop = asyncio.get_event_loop()
worker = PythonWorker()

loop.run_until_complete(worker.connect())
loop.run_until_complete(worker.run())
