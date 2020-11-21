import asyncio
import enum

import utils.time_utils as tutils
import rpc_server as rpcif
import common.log as log

from common.event import EventType


class RPCServicer(rpcif.Servicer):
    _crt_base_id = "%s" % tutils.tnow()
    _pm_seq = 0

    class RemotePM:
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

        async def enqueue_event(self, ev_type, payload):
            await self.queue.put((ev_type, payload))

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
            await pm.enqueue_event(EventType.message, payload)

    async def send_on_ready(self):
        """
        Sends on_ready event to all plugin managers
        """
        for pm in self.pm_id_to_name.values():
            await pm.enqueue_event(EventType.on_ready, None)

    async def new_plugin_manager(self, new_pm_name):
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
            reply_id = "%s_%s" % (RPCServicer._crt_base_id, RPCServicer._pm_seq)
            self.pm_id_to_name[reply_id] = RPCServicer.RemotePM(new_pm_name, reply_id)
            self.logger.info(f"PM registered as : {reply_id}")

            RPCServicer._pm_seq += 1

        # Enqueue on_ready when it's going to connect
        if self.bot.is_ready:
            await self.pm_id_to_name[reply_id].queue.put((EventType.on_ready, None))

        return reply_id

    def set_command_list(self, pm_id, cmd_list):
        """
        Called when a PM sets the command list
        """
        if pm_id not in self.pm_id_to_name.keys():
            self.logger.error(
                f"Got request from unknown PM ID {pm_id} exposing: {cmd_list}"
            )
            return []

        self.logger.info(f"Plugin manager with ID {pm_id} exposes: {cmd_list}")

        # TODO parse cmd list
        return cmd_list

    async def get_raw_event(self, pm_id, req_list):
        # If this fails, it's fine - client will fail too
        pm_inst = self.pm_id_to_name[pm_id]

        # Wait for event
        evt_type, evt = await pm_inst.queue.get()

        return evt_type, evt

    def get_servers(self):
        return self.backend.get_server_ids()

    def get_server(self, sid):
        return self.backend.get_server(sid)

    def get_users(self, server_id):
        return self.backend.get_users(server_id)

    def get_role(self, role_id, server_id):
        return self.backend.get_role(role_id, server_id)

    def get_user(self, user_id, server_id):
        return self.backend.get_user(user_id, server_id)

    async def send_message(self, text, channel_id, server_id):
        """
        Send message
        """
        msg = await self.backend.send_message(text, channel_id, server_id)
        return msg.id

    async def send_embed(
        self,
        title,
        description,
        fields,
        inline_fields,
        image_url,
        footer_txt,
        channel_id,
        server_id
    ):
        embed = self.backend.prepare_embed(
            title=title,
            description=description,
            fields=fields,
            inline_fields=inline_fields,
            image_url=image_url,
            footer_txt=footer_txt,
        )

        msg = await self.backend.send_embed(embed, channel_id, server_id)
        return msg.id

    async def send_file(self, data, fname, channel_id, server_id):
        msg = await self.backend.send_file(data, fname, channel_id, server_id)
        return msg.id

    async def get_attachments(self, message_id, channel_id, server_id):
        return await self.backend.get_attachments(message_id, channel_id, server_id)