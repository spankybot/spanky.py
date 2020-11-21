import grpc

from rpc import gen_code
from rpc import spanky_pb2
from rpc.spanky_pb2_grpc import add_SpankyServicer_to_server, SpankyServicer
from concurrent import futures
import common.log as log
import bot


logger = log.botlog("rpc_server", console_level=log.loglevel.DEBUG)


class ImplementMe:
    def new_plugin_manager(self, new_pm_name):
        raise NotImplementedError()

    def set_command_list(self, pm_id, cmd_list):
        raise NotImplementedError()

    def send_message(self, text, channel_id, server_id):
        raise NotImplementedError()

    def get_raw_event(self, pm_id, req_list):
        raise NotImplementedError()

    def get_servers(self):
        raise NotImplementedError()

    def get_server(self, sid):
        raise NotImplementedError()

    def get_role(self, role_id, server_id):
        raise NotImplementedError()

    def get_user(self, user_id, server_id):
        raise NotImplementedError()

    def get_users(self, server_id):
        raise NotImplementedError()

    def send_embed(
        self,
        title,
        description,
        fields,
        inline_fields,
        image_url,
        footer_txt,
        channel_id,
        server_id,
    ):
        raise NotImplementedError()

    def send_file(self, data, fname, channel_id, server_id):
        raise NotImplementedError()

    def get_attachments(self, message_id, channel_id, server_id):
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
        field = request.WhichOneof("payload")

        if field == "msg":
            return spanky_pb2.SomeObjectID(
                id=await self.send_message(
                    text=request.msg.text,
                    channel_id=request.channel_id,
                    server_id=request.server_id,
                )
            )
        elif field == "embed":
            fields = {}
            for field in request.embed.fields:
                fields[field.name] = field.text

            return spanky_pb2.SomeObjectID(
                id=await self.send_embed(
                    title=request.embed.title,
                    description=request.embed.description,
                    fields=fields,
                    inline_fields=request.embed.inline_fields,
                    image_url=request.embed.image_url,
                    footer_txt=request.embed.footer_txt,
                    channel_id=request.channel_id,
                    server_id=request.server_id,
                )
            )

        elif field == "file":
            return spanky_pb2.SomeObjectID(
                id=await self.send_file(
                    data=request.file.data,
                    fname=request.file.fname,
                    channel_id=request.channel_id,
                    server_id=request.server_id,
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

    async def GetServer(self, request, context):
        obj = self.get_server(request.id)
        return obj.serialize()

    async def GetServerIDs(self, request, context):
        server_list = self.get_servers()

        return spanky_pb2.ObjectIDList(ids=[i.id for i in server_list])

    async def GetUsers(self, request, context):
        ulist = self.get_users(request.id)

        return spanky_pb2.UserList(user_list=[i.serialize() for i in ulist])

    async def GetRole(self, request, context):
        obj = self.get_role(request.role_id, request.server_id)
        return obj.serialize()

    async def GetUserByID(self, request, context):
        obj = self.get_user(request.user_id, request.server_id)
        return obj.serialize()

    async def GetAttachments(self, request, context):
        try:
            obj = await self.get_attachments(
                request.message_id, request.channel_id, request.server_id
            )

            return spanky_pb2.Attachments(urls=[i for i in obj])
        except:
            import traceback

            traceback.print_exc()


async def init_grpc_server(servicer):
    server = grpc.aio.server()
    add_SpankyServicer_to_server(servicer, server)

    server.add_insecure_port("localhost:5151")
    await server.start()
    logger.info("Started GRPC server")

    return server, servicer
