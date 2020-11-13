import grpc

from rpc import gen_code
from rpc import spanky_pb2
from rpc.spanky_pb2_grpc import add_SpankyServicer_to_server, SpankyServicer
from concurrent import futures
import common.log as log
import bot


logger = log.botlog("rpc_server", console_level=log.loglevel.DEBUG)


class ImplementMe:
    async def new_plugin_manager(self, new_pm_name):
        raise NotImplementedError()

    def set_command_list(self, pm_id, cmd_list):
        raise NotImplementedError()

    async def send_message(self, text, channel_id):
        raise NotImplementedError()

    async def get_raw_event(self, pm_id, req_list):
        raise NotImplementedError()

    async def get_servers(self, pm_id):
        raise NotImplementedError()

    async def send_embed(
        self,
        title,
        description=None,
        fields=None,
        inline_fields=True,
        image_url=None,
        footer_txt=None,
        channel_id=-1,
    ):
        raise NotImplementedError()


class Servicer(SpankyServicer, ImplementMe):
    async def NewPluginManager(self, request, context):
        return spanky_pb2.AckPM(
            PluginMgrID=await self.new_plugin_manager(request.PluginMgrName)
        )

    async def SetCommandList(self, request, context):
        return spanky_pb2.RespCmdList(
            CmdResponseList=self.set_command_list(
                pm_id=request.PluginMgrID, cmd_list=request.CmdRequestList
            )
        )

    async def SendMessage(self, request, context):
        return spanky_pb2.SomeObjectID(
            id=await self.send_message(text=request.text, channel_id=request.channel_id)
        )

    async def SendEmbed(self, request, context):

        fields = {}
        for field in request.fields:
            fields[field.name] = field.text

        return spanky_pb2.SomeObjectID(
            id=await self.send_embed(
                title=request.title,
                description=request.description,
                fields=fields,
                inline_fields=request.inline_fields,
                image_url=request.image_url,
                footer_txt=request.footer_txt,
                channel_id=request.channel_id,
            )
        )

    async def GetEvent(self, request, context):
        while True:
            evt_type, payload = await self.get_raw_event(
                request.PluginMgrID, request.EventList
            )

            # TODO could EventType import be avoided?
            if evt_type == bot.EventType.message:
                yield spanky_pb2.Event(event_type=evt_type, msg=payload.serialize())
            elif evt_type == bot.EventType.on_ready:
                yield spanky_pb2.Event(event_type=evt_type)
            else:
                return

    async def GetServers(self, request, context):
        server_list = self.get_servers(request.PluginMgrID)

        return spanky_pb2.RespServers(slist=[i.serialize() for i in server_list])


async def init_grpc_server(servicer):
    server = grpc.aio.server()
    add_SpankyServicer_to_server(servicer, server)

    server.add_insecure_port("localhost:5151")
    await server.start()
    logger.info("Started GRPC server")

    return server, servicer
