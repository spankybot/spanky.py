import asyncio
import json
import logging
import re
import threading
import importlib
import time

import pluginmgr_handler
import common.log as log

import rpc_server as rpcif
from pluginmgr_handler import EventType


class Bot():
    def __init__(self, input_type):
        # Create loggers
        self.logger = log.botlog("spanky", console_level=log.loglevel.DEBUG)
        self.audit = log.botlog("audit", console_level=log.loglevel.DEBUG)

        self.logger.info("Initializing bot")

        self.user_agent = "spaky.py bot https://github.com/gc-plp/spanky.py"
        self.is_ready = False
        self.loop = asyncio.get_event_loop()

        # Open the bot config file
        with open('bot_config.json') as data_file:
            self.config = json.load(data_file)

        # Import the backend
        try:
            module = importlib.import_module("inputs.%s" % input_type)
            self.input = module
        except:
            import traceback
            import sys
            print(traceback.format_exc())
            sys.exit(1)

    async def start(self):

        # Initialize the backend module
        self.logger.info("Starting backend")
        self.backend = self.input.Init(self)

        # Initialize the GRPC server
        self.rpc_server, self.servicer = await rpcif.init_grpc_server(
            pluginmgr_handler.RPCServicer(self, self.backend))

        asyncio.run_coroutine_threadsafe(
            self.rpc_server.wait_for_termination(), self.loop)

        await self.backend.do_init()
        self.logger.info("Started backend")

    async def ready(self):
        # Send on-ready to all connected plugin managers
        await self.servicer.send_on_ready()

        self.is_ready = True

    def on_periodic(self):
        pass

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
        pass

    def on_bulk_message_delete(self, messages):
        """On message bulk delete external hook"""
        pass

    def on_message_edit(self, before, after):
        """On message edit external hook"""
        pass

    async def on_message(self, message):
        """On message external hook"""
        await self.servicer.dispatch_message(message)

# ----------------
# Member events
# ----------------
    def on_member_update(self, before, after):
        pass

    def on_member_join(self, member):
        pass

    def on_member_remove(self, member):
        pass

    def on_member_ban(self, server, member):
        pass

    def on_member_unban(self, server, member):
        pass

# ----------------
# Reaction events
# ----------------
    def on_reaction_add(self, reaction, user):
        pass

    def on_reaction_remove(self, reaction, user):
        pass
