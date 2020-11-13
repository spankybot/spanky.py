import asyncio
import grpc

from rpc import gen_code
from rpc import spanky_pb2
from rpc import spanky_pb2_grpc
from common.event import EventType

import rpc.rpc_objects as rpcobj

import common.log as log

logger = log.botlog("rpc_client", console_level=log.loglevel.DEBUG)

# TODO hack for now
global_cli = None
loop = asyncio.get_event_loop()


class SServer(rpcobj.Server):
    def __init__(self, sid, name):
        self.id = str(sid)
        self.name = name


class SUser(rpcobj.User):
    def __init__(self, uid, name, display_name):
        self.id = str(uid)
        self.name = name
        self.display_name = display_name


class CMessage(rpcobj.Message):
    def __init__(self, content, message_id, author, server_id, channel_id):
        self.content = content
        self.id = str(message_id)
        self.author = author
        self.server_id = str(server_id)
        self.channel_id = str(channel_id)

    def reply(self, text):
        asyncio.run_coroutine_threadsafe(
            global_cli.send_message(text=text, channel_id=self.channel_id), loop
        )

    def reply_embed(
        self,
        title,
        description="",
        fields=None,
        inline_fields=True,
        image_url=None,
        footer_txt=None,
    ):
        fields_list = []
        for key, val in fields.items():
            fields_list.append(
                spanky_pb2.EmbedField(
                    name=key,
                    text=val)
                )

        asyncio.run_coroutine_threadsafe(
            global_cli.send_embed(
                title=title,
                description=description,
                fields=fields_list,
                inline_fields=inline_fields,
                image_url=image_url,
                footer_txt=footer_txt,
                channel_id=self.channel_id), loop
        )


class RPCClient:
    def __init__(self, server_addr, register_name):
        self.register_name = register_name
        self.server_addr = server_addr

        global global_cli
        global_cli = self

    async def connect(self):
        self.server_conn = await self._connect_to_server(self.server_addr)

        # Register to the server
        register_resp = await self.server_conn.NewPluginManager(
            spanky_pb2.NewPM(PluginMgrName="testplm")
        )
        # Save our client ID
        self.my_server_id = register_resp.PluginMgrID

        self.valid_commands = []

    async def _connect_to_server(self, server_addr):
        """
        Connect to a server and return the stub
        """
        logger.info(f"Connecting to {server_addr}")

        channel = grpc.aio.insecure_channel("localhost:5151")
        stub = spanky_pb2_grpc.SpankyStub(channel)

        return stub

    async def get_event(self):
        call = self.server_conn.GetEvent(
            spanky_pb2.GetEventReq(PluginMgrID=self.my_server_id)
        )

        evt = await call.read()

        if evt.event_type == EventType.message:
            return evt.event_type, CMessage.deserialize(evt.msg)
        elif evt.event_type == EventType.on_ready:
            return evt.event_type, None

    #
    # Exportables
    #

    async def set_command_list(self, cmd_list):
        """
        Send the command list and return the result
        """
        # Send the command list
        cmdlist_resp = self.server_conn.SetCommandList(
            spanky_pb2.ReqCmdList(
                PluginMgrID=self.my_server_id, CmdRequestList=cmd_list
            )
        )

        return cmdlist_resp.CmdResponseList

    async def send_message(self, text, channel_id):
        """
        Send a message to the server
        """
        return await self.server_conn.SendMessage(
            spanky_pb2.OutgoingMessage(channel_id=int(channel_id), text=text)
        )

    async def send_embed(
        self,
        title,
        description,
        fields,
        inline_fields,
        image_url,
        footer_txt,
        channel_id):
        """
        Send a message to the server
        """

        return await self.server_conn.SendEmbed(
            spanky_pb2.OutgoingEmbed(
                title=title,
                description=description,
                fields=fields,
                inline_fields=inline_fields,
                image_url=image_url,
                footer_txt=footer_txt,
                channel_id=int(channel_id))
            )

    async def get_servers(self):
        # Ask for server list
        server_list_resp = await self.server_conn.GetServers(
            spanky_pb2.AckPM(
                PluginMgrID=self.my_server_id,
            )
        )

        return [rpcobj.Server.deserialize(i) for i in server_list_resp.slist]
