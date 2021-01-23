import asyncio
import json
import importlib
from . import pluginmgr_handler
from . import rpc_server as rpcif

from SpankyCommon.utils import log
from SpankyCommon.utils import bot_utils as butils


import SpankyWorker


class Bot:
    def __init__(self, input_type):
        # Create loggers
        self.logger = log.botlog("spanky", console_level=log.loglevel.DEBUG)
        self.audit = log.botlog("audit", console_level=log.loglevel.DEBUG)

        self.logger.info("Initializing bot")

        self.user_agent = "spaky.py bot https://github.com/gc-plp/spanky.py"
        self.is_ready = False
        self.loop = asyncio.get_event_loop()

        # Open the bot config file
        with open("bot_config.json") as data_file:
            self.config = json.load(data_file)

        # Import the backend
        try:
            module = importlib.import_module(
                "SpankyServer.inputs.%s" % input_type)
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
        self.rpc_server, self.servicer = await rpcif.init_grpc_server()

        # Initialize the handler
        self.handler = pluginmgr_handler.Handler(self, self.backend)
        self.local_handler = pluginmgr_handler.SyncHandler(self, self.backend)

        # Tell the servicer who handles calls
        self.servicer.set_handler(self.handler)
        butils.run_in_thread(self.launch_local_pm)

        asyncio.run_coroutine_threadsafe(
            self.rpc_server.wait_for_termination(), self.loop
        )

        await self.backend.do_init()
        self.logger.info("Started backend")

    def launch_local_pm(self):
        worker = SpankyWorker.PythonWorker(self.local_handler)
        worker.connect()
        worker.run()

    async def ready(self):
        # Send on-ready to all connected plugin managers
        await self.handler.send_on_ready()
        await self.local_handler.send_on_ready()

        self.is_ready = True

    def on_periodic(self):
        pass

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
        pass

    async def on_bulk_message_delete(self, messages):
        """On message bulk delete external hook"""
        pass

    async def on_message_edit(self, before, after):
        """On message edit external hook"""
        pass

    async def on_message(self, message):
        """On message external hook"""
        self.handler.dispatch_message(message)
        self.local_handler.dispatch_message(message)

    # ----------------
    # Member events
    # ----------------
    async def on_member_update(self, before, after):
        pass

    async def on_member_join(self, member):
        pass

    async def on_member_remove(self, member):
        pass

    async def on_member_ban(self, server, member):
        pass

    async def on_member_unban(self, server, member):
        pass

    # ----------------
    # Reaction events
    # ----------------
    async def on_reaction_add(self, reaction, user):
        pass

    async def on_reaction_remove(self, reaction, user):
        pass
