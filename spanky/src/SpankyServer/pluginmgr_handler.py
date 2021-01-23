import asyncio
import threading
import SpankyCommon.utils.time_utils as tutils

from SpankyCommon.utils import log
from SpankyCommon.event import EventType


class PMManager:
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

        def enqueue_event(self, ev_type, payload):
            self.queue.put_nowait((ev_type, payload))

    def __init__(self):
        # Map of plugin manager id -> RemotePM
        self.pm_id_to_name = {}
        self.logger = log.botlog("PMManager", console_level=log.loglevel.DEBUG)

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
            reply_id = "%s_%s" % (PMManager._crt_base_id, PMManager._pm_seq)
            self.pm_id_to_name[reply_id] = PMManager.RemotePM(
                new_pm_name, reply_id
            )
            self.logger.info(f"PM registered as : {reply_id}")

            PMManager._pm_seq += 1

        return reply_id

    def get_pm_list(self):
        for pm in self.pm_id_to_name.values():
            yield pm

    def get_pm(self, pm_id):
        return self.pm_id_to_name[pm_id]


class Handler:
    def __init__(self, bot, backend):
        self.bot = bot
        self.backend = backend
        self.logger = log.botlog("rpcif", console_level=log.loglevel.DEBUG)

        self.pmmgr = PMManager()

    def dont_sync(func):
        setattr(func, "dont_sync", True)
        return func

    async def connect(self, name):
        return await self.new_plugin_manager(name)

    def dispatch_message(self, payload):
        for pm in self.pmmgr.get_pm_list():
            pm.enqueue_event(EventType.message, payload)

    @dont_sync
    async def send_on_ready(self):
        """
        Sends on_ready event to all plugin managers
        """
        for pm in self.pmmgr.get_pm_list():
            pm.enqueue_event(EventType.on_ready, None)

    @dont_sync
    async def new_plugin_manager(self, new_pm_name):
        """
        Called when a new plugin manager is registered

        Each worker has to have an unique name.
        """
        pm_id = self.pmmgr.new_plugin_manager(new_pm_name)

        # Enqueue on_ready when it's going to connect
        if self.bot.is_ready:
            self.pmmgr.get_pm(pm_id).queue.put_nowait(
                (EventType.on_ready, None)
            )

        return pm_id

    def set_command_list(self, pm_id, cmd_list):
        """
        Called when a PM sets the command list
        """
        pm = self.pmmgr.get_pm(pm_id)
        if not pm:
            self.logger.error(
                f"Got request from unknown PM ID {pm_id} exposing: {cmd_list}"
            )
            return []

        self.logger.info(f"Plugin manager with ID {pm_id} exposes: {cmd_list}")

        # TODO parse cmd list
        return cmd_list

    async def get_event(self, pm_id, req_list):
        # If this fails, it's fine - client will fail too
        pm_inst = self.pmmgr.get_pm(pm_id)

        # Wait for event
        evt_type, evt = await pm_inst.queue.get()

        return evt_type, evt

    def get_servers(self):
        return self.backend.get_server_ids()

    def get_server(self, sid):
        return self.backend.get_server(sid)

    def get_users(self, server_id):
        return self.backend.get_users(server_id)

    def get_role(self, role_id, role_name, server_id):
        return self.backend.get_role(role_id, role_name, server_id)

    def get_user(self, user_id, user_name, server_id):
        return self.backend.get_user(user_id, user_name, server_id)

    async def send_message(self, text, channel_id, server_id, source_msg_id):
        """
        Send message
        """
        msg = await self.backend.send_message(
            text, channel_id, server_id, source_msg_id
        )
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
        server_id,
        source_msg_id,
    ):
        embed = self.backend.prepare_embed(
            title=title,
            description=description,
            fields=fields,
            inline_fields=inline_fields,
            image_url=image_url,
            footer_txt=footer_txt,
        )

        msg = await self.backend.send_embed(
            embed, channel_id, server_id, source_msg_id
        )
        return msg.id

    async def send_file(
        self, data, fname, channel_id, server_id, source_msg_id
    ):
        msg = await self.backend.send_file(
            data, fname, channel_id, server_id, source_msg_id
        )
        return msg.id

    async def get_attachments(self, message_id, channel_id, server_id):
        return await self.backend.get_attachments(
            message_id, channel_id, server_id
        )

    async def add_roles(self, user_id, server_id, roleid_list):
        return await self.backend.add_roles(user_id, server_id, roleid_list)

    async def remove_roles(self, user_id, server_id, roleid_list):
        return await self.backend.remove_roles(user_id, server_id, roleid_list)

    async def send_pm(self, user_id, text):
        pm = await self.backend.send_pm(user_id, text)
        return pm.id

    async def get_channel(self, channel_id, channel_name, server_id):
        return await self.backend.get_channel(
            channel_id, channel_name, server_id
        )

    async def delete_message(self, *args, **kwargs):
        return await self.backend.delete_message(*args, **kwargs)

    async def get_bot_id(self, *args, **kwargs):
        return self.backend.get_bot_id(*args, **kwargs)

    async def add_reaction(self, *args, **kwargs):
        return await self.backend.add_reaction(*args, **kwargs)

    async def remove_reaction(self, *args, **kwargs):
        return await self.backend.remove_reaction(*args, **kwargs)


class SyncHandler(Handler):
    pass

loop = asyncio.get_event_loop()

def do_replace(fname, func):
    def call_it(*args, **kwargs):
        async def async_call_it(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except:
                import traceback

                traceback.print_exc()

        future = asyncio.run_coroutine_threadsafe(
            async_call_it(*args, **kwargs), loop
        )
        if threading.main_thread() != threading.current_thread():
            result = future.result()

            return result
        else:
            # If running from the main thread nothing can be returned
            return None

    call_it.__name__ = fname
    setattr(SyncHandler, fname, call_it)


for fname, func in Handler.__dict__.items():
    if not asyncio.iscoroutinefunction(func):
        continue

    if hasattr(func, "dont_sync"):
        continue

    do_replace(fname, func)
