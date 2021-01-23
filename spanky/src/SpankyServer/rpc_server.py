import grpc

from SpankyCommon.rpc import generate_from_proto
generate_from_proto()

from SpankyCommon.rpc import spanky_pb2
from SpankyCommon.rpc.spanky_pb2_grpc import (
    add_SpankyServicer_to_server,
    SpankyServicer,
)
from SpankyCommon.utils import log
from SpankyCommon.event import EventType

logger = log.botlog("rpc_server", console_level=log.loglevel.DEBUG)


class Servicer(SpankyServicer):
    def log_call(func):
        async def call_it(*args, **kwargs):
            try:
                print(f"-> CALL {func.__name__} with params {args} {kwargs}")
                rval = await func(*args, **kwargs)
                print(f"<- RTRN {func.__name__} value {rval}")

                return rval
            except:
                import traceback

                traceback.print_exc()

        return call_it

    def set_handler(self, handler):
        self.handler = handler

    @log_call
    async def NewPluginManager(self, request, context):
        return spanky_pb2.AckPM(
            PluginMgrID=await self.handler.new_plugin_manager(
                request.PluginMgrName
            )
        )

    @log_call
    async def SetCommandList(self, request, context):
        return spanky_pb2.RespCmdList(
            CmdResponseList=self.handler.set_command_list(
                pm_id=request.PluginMgrID, cmd_list=request.CmdRequestList
            )
        )

    @log_call
    async def SendMessage(self, request, context):
        field = request.WhichOneof("payload")

        if field == "msg":
            return spanky_pb2.SomeObjectID(
                id=await self.handler.send_message(
                    text=request.msg.text,
                    channel_id=request.channel_id,
                    server_id=request.server_id,
                    source_msg_id=request.source_msg_id,
                )
            )
        elif field == "embed":
            fields = {}
            for field in request.embed.fields:
                fields[field.name] = field.text

            return spanky_pb2.SomeObjectID(
                id=await self.handler.send_embed(
                    title=request.embed.title,
                    description=request.embed.description,
                    fields=fields,
                    inline_fields=request.embed.inline_fields,
                    image_url=request.embed.image_url,
                    footer_txt=request.embed.footer_txt,
                    channel_id=request.channel_id,
                    server_id=request.server_id,
                    source_msg_id=request.source_msg_id,
                )
            )

        elif field == "file":
            return spanky_pb2.SomeObjectID(
                id=await self.handler.send_file(
                    data=request.file.data,
                    fname=request.file.fname,
                    channel_id=request.channel_id,
                    server_id=request.server_id,
                    source_msg_id=request.source_msg_id,
                )
            )

    async def GetEvent(self, request, context):
        while True:
            evt_type, payload = await self.handler.get_event(
                request.PluginMgrID, request.EventList
            )

            # TODO could EventType import be avoided?
            if evt_type == EventType.message:
                yield spanky_pb2.Event(
                    event_type=evt_type, msg=payload.serialize()
                )
            elif evt_type == EventType.on_ready:
                yield spanky_pb2.Event(event_type=evt_type)
            else:
                return

    @log_call
    async def GetServer(self, request, context):
        obj = self.handler.get_server(request.id)
        return obj.serialize()

    @log_call
    async def GetServerIDs(self, request, context):
        server_list = self.handler.get_servers()

        return spanky_pb2.ObjectIDList(ids=[i.id for i in server_list])

    @log_call
    async def GetUsers(self, request, context):
        ulist = self.handler.get_users(request.id)

        return spanky_pb2.UserList(user_list=[i.serialize() for i in ulist])

    @log_call
    async def GetRole(self, request, context):
        obj = self.handler.get_role(
            request.role_id, request.role_name, request.server_id
        )
        return obj.serialize()

    @log_call
    async def GetUser(self, request, context):
        obj = self.handler.get_user(
            request.user_id, request.user_name, request.server_id
        )
        return obj.serialize()

    @log_call
    async def GetAttachments(self, request, context):
        try:
            obj = await self.handler.get_attachments(
                request.message_id, request.channel_id, request.server_id
            )

            return spanky_pb2.Attachments(urls=[i for i in obj])
        except:
            import traceback

            traceback.print_exc()

    @log_call
    async def AddRoles(self, request, context):
        await self.handler.add_roles(
            request.user_id, request.server_id, request.roleid_list
        )
        return spanky_pb2.Empty()

    @log_call
    async def RemoveRoles(self, request, context):
        await self.handler.remove_roles(
            request.user_id, request.server_id, request.roleid_list
        )
        return spanky_pb2.Empty()

    @log_call
    async def SendPM(self, request, context):
        return spanky_pb2.SomeObjectID(
            id=await self.handler.send_pm(
                user_id=request.user_id, text=request.msg.text
            )
        )

    @log_call
    async def GetChannel(self, request, context):
        chan = await self.handler.get_channel(
            channel_id=request.channel_id,
            channel_name=request.channel_name,
            server_id=request.server_id,
        )
        return chan.serialize()

    @log_call
    async def DeleteMessage(self, request, context):
        chan = await self.handler.delete_message(
            message_id=request.message_id,
            channel_id=request.channel_id,
            server_id=request.server_id,
        )
        return chan.serialize()

    @log_call
    async def GetBotID(self, request, context):
        chan = await self.handler.delete_message(
            message_id=request.message_id,
            channel_id=request.channel_id,
            server_id=request.server_id,
        )
        return chan.serialize()

    @log_call
    async def AddReaction(self, request, context):
        bot_id = await self.handler.get_bot_id()
        return spanky_pb2.SomeObjectID(
            id=bot_id
        )

    @log_call
    async def RemoveReaction(self, request, context):
        pass

    # @log_call
    # async def GetMessagesFromChannel(self, request, context):
    #     msg_list = await self.handler.get_messages(
    #         count=request.count,
    #         before_ts=request.before_ts,
    #         after_ts=request.after_ts,
    #         channel_id=request.channel_id,
    #         server_id=request.server_id
    #     )
    #     return spanky_pb2.MessageList(

    #     )



async def init_grpc_server():
    server = grpc.aio.server()
    servicer = Servicer()

    add_SpankyServicer_to_server(servicer, server)

    server.add_insecure_port("localhost:5151")
    await server.start()
    logger.info("Started GRPC server")

    return server, servicer
