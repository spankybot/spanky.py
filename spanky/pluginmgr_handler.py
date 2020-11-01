import asyncio
import enum

import utils.time_utils as tutils
import rpc_server as rpcif
import common.log as log

from common.event import EventType


class RPCServicer(rpcif.Servicer):
    _crt_base_id = "%s" % tutils.tnow()
    _pm_seq = 0

    class RemotePM():
        """
        Remote plugin manager instance
        """

        def __init__(self, name, pmid):
            self.name = name
            self.id = pmid

            self.queue = asyncio.Queue()
            self.commands = []
            self.waiting_work = False

        def set_cmds(self, cmd_list):
            self.commands = cmd_list

    def __init__(self, bot, backend):
        self.bot = bot
        self.backend = backend
        self.logger = log.botlog("rpcif", console_level=log.loglevel.DEBUG)

        # Map of plugin manager id -> RemotePM
        self.pm_id_to_name = {}

    def is_command(self, text):
        pass

    async def dispatch_message(self, payload):
        for pm in self.pm_id_to_name.values():
            await pm.queue.put((EventType.message, payload))

    async def send_on_ready(self):
        """
        Sends on_ready event to all plugin managers
        """
        for pm in self.pm_id_to_name.values():
            await pm.queue.put((EventType.on_ready, None))

    def new_plugin_manager(self, new_pm_name):
        """
        Called when a new plugin manager is registered

        Each worker has to have an unique name.
        """
        reply_id = None

        self.logger.info(f"New plugin manager request: {new_pm_name}")

        # Check if previously registered
        for pm_id, pm_inst in self.pm_id_to_name.items():
            if pm_inst.name == new_pm_name:
                reply_id = pm_id
                self.logger.info(f"PM previously registered as: {pm_id}")

        if not reply_id:
            # Create a new ID and save it
            reply_id = "%s_%s" % (
                RPCServicer._crt_base_id, RPCServicer._pm_seq)
            self.pm_id_to_name[reply_id] = RPCServicer.RemotePM(
                new_pm_name, reply_id)
            self.logger.info(f"PM registered as : {reply_id}")

            RPCServicer._pm_seq += 1

        return reply_id

    def set_command_list(self, pm_id, cmd_list):
        """
        Called when a PM sets the command list
        """
        if pm_id not in self.pm_id_to_name.keys():
            self.logger.error(
                f"Got request from unknown PM ID {pm_id} exposing: {cmd_list}")
            return []

        self.logger.info(
            f"Plugin manager with ID {pm_id} exposes: {cmd_list}")

        # TODO parse cmd list
        return cmd_list

    async def get_raw_event(self, pm_id, req_list):
        # If this fails, it's fine - client will fail too
        pm_inst = self.pm_id_to_name[pm_id]

        # Wait for event
        evt_type, evt = await pm_inst.queue.get()

        return evt_type, evt

    async def send_message(self, text, channel_id):
        """
        Send message
        """

        channel = self.backend.client.get_channel(channel_id)
        msg = await channel.send(content=text)

        return msg.id

    def get_servers(self, pm_id):
        return self.backend.get_servers()
