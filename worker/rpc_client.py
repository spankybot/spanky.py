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


class PWMessage(rpcobj.Message):
    def send_message(self, text, channel_id):
        print(text)
        asyncio.run_coroutine_threadsafe(
            global_cli.send_message(text=text, channel_id=channel_id),
            loop)


class RPCClient():
    def __init__(self, server_addr, register_name):
        self.register_name = register_name
        self.server_addr = server_addr

        global global_cli
        global_cli = self

    async def connect(self):
        self.server_conn = await self._connect_to_server(self.server_addr)

        # Register to the server
        register_resp = await self.server_conn.NewPluginManager(
            spanky_pb2.NewPM(
                PluginMgrName="testplm"
            )
        )
        # Save our client ID
        self.my_server_id = register_resp.PluginMgrID

        self.valid_commands = []

    async def _connect_to_server(self, server_addr):
        """
        Connect to a server and return the stub
        """
        logger.info(f"Connecting to {server_addr}")

        channel = grpc.aio.insecure_channel('localhost:5151')
        stub = spanky_pb2_grpc.SpankyStub(channel)

        return stub

    async def set_command_list(self, cmd_list):
        """
        Send the command list and return the result
        """
        # Send the command list
        cmdlist_resp = self.server_conn.SetCommandList(
            spanky_pb2.ReqCmdList(
                PluginMgrID=self.my_server_id,
                CmdRequestList=cmd_list
            )
        )

        return cmdlist_resp.CmdResponseList

    async def send_message(self, text, channel_id):
        """
        Send a message to the server
        """
        self.server_conn.SendMessage(spanky_pb2.OutgoingMessage(
            channel_id=int(channel_id), text=text))

    async def get_servers(self):
        # Ask for server list
        server_list_resp = await self.server_conn.GetServers(
            spanky_pb2.AckPM(
                PluginMgrID=self.my_server_id,
            )
        )

        return[rpcobj.Server.deserialize(i) for i in server_list_resp.slist]

    async def get_event(self):
        call = self.server_conn.GetEvent(
            spanky_pb2.GetEventReq(
                PluginMgrID=self.my_server_id))

        evt = await call.read()

        if evt.event_type == EventType.message:
            return evt.event_type, PWMessage.deserialize(evt.msg)
        elif evt.event_type == EventType.on_ready:
            return evt.event_type, None
