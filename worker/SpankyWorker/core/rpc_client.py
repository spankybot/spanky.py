import grpc
import io

from SpankyCommon.rpc import spanky_pb2
from SpankyCommon.rpc import spanky_pb2_grpc

from SpankyCommon.utils import log

from .client import CServer, CChannel, CRole, CMessage

logger = log.botlog("rpc_client", console_level=log.loglevel.DEBUG)

# TODO hack for now
global_cli = None


class RPCClient:
    MAX_FILE_SIZE = 20 * 1024 * 1024
    _logger = log.botlog("rpc_client")

    # def create_call(self, func, name):
    #     def call_it(*args, **kwargs):
    #         async def call_async(*args, **kwargs):
    #             return await func(*args, **kwargs)

    #         return butils.run_async_wait(
    #             call_async, args=args, kwargs=kwargs)

    #     setattr(self, name, call_it)

    def __init__(self, server_addr):
        self.register_name = None
        self.server_addr = server_addr

        global global_cli
        global_cli = self

    def log_call(func):
        import asyncio

        async def call_it_async(*args, **kwargs):
            try:
                print(">>>")
                print(f"-> CALL {func.__name__} with params {args} {kwargs}")
                rval = await func(*args, **kwargs)
                print("---")
                print(f"<- RTRN {func.__name__} value {rval}")
                print("###")

                return rval
            except:
                import traceback

                traceback.print_exc()

        def call_it_sync(*args, **kwargs):
            try:
                print(">>>")
                print(f"-> CALL {func.__name__} with params {args} {kwargs}")
                rval = func(*args, **kwargs)
                print("---")
                print(f"<- RTRN {func.__name__} value {rval}")
                print("###")

                return rval
            except:
                import traceback

                traceback.print_exc()

        if asyncio.iscoroutinefunction(func):
            return call_it_async
        else:
            return call_it_sync

    def connect(self, register_name):
        self.register_name = register_name
        self.server_conn = self._connect_to_server(self.server_addr)

        # Register to the server
        register_resp = self.server_conn.NewPluginManager(
            spanky_pb2.NewPM(PluginMgrName="testplm")
        )
        # Save our client ID
        self.valid_commands = []

        return register_resp.PluginMgrID

    def _connect_to_server(self, server_addr):
        """
        Connect to a server and return the stub
        """
        logger.info(f"Connecting to {server_addr}")

        channel = grpc.insecure_channel("localhost:5151")
        stub = spanky_pb2_grpc.SpankyStub(channel)

        return stub

    @log_call
    def get_event(self, my_server_id, cmd_list):
        for val in self.server_conn.GetEvent(
            spanky_pb2.GetEventReq(PluginMgrID=my_server_id, EventList=0)
        ):
            if val.HasField("msg"):
                return val.event_type, val.msg
            else:
                return val.event_type, None

    @log_call
    def set_command_list(self, my_server_id, cmd_list):
        """
        Send the command list and return the result
        """
        # Send the command list
        cmdlist_resp = self.server_conn.SetCommandList(
            spanky_pb2.ReqCmdList(
                PluginMgrID=my_server_id, CmdRequestList=cmd_list
            )
        )

        return cmdlist_resp.CmdResponseList

    @log_call
    def send_message(self, text, channel_id, server_id, source_msg_id):
        """
        Send a message
        """
        msg_id = self.server_conn.SendMessage(
            spanky_pb2.OutgoingThing(
                channel_id=channel_id,
                server_id=server_id,
                source_msg_id=source_msg_id,
                msg=spanky_pb2.OutgoingMessage(text=text),
            )
        )

        return CMessage.from_id(msg_id, server_id)

    @log_call
    def send_embed(
        self,
        title,
        description,
        fields,
        inline_fields,
        image_url,
        footer_txt,
        channel_id,
        source_msg_id,
        server_id,
    ):
        """
        Send an embed
        """
        fields_list = []
        for key, val in fields.items():
            fields_list.append(spanky_pb2.EmbedField(name=key, text=val))

        msg_id = self.server_conn.SendMessage(
            spanky_pb2.OutgoingThing(
                channel_id=channel_id,
                source_msg_id=source_msg_id,
                server_id=server_id,
                embed=spanky_pb2.OutgoingEmbed(
                    title=title,
                    description=description,
                    fields=fields_list,
                    inline_fields=inline_fields,
                    image_url=image_url,
                    footer_txt=footer_txt,
                ),
            )
        )

        return CMessage.from_id(msg_id, server_id)

    @log_call
    def send_file(
        self, file_descriptor, fname, channel_id, server_id, source_msg_id
    ):
        """
        Send a file
        """
        buffer = file_descriptor.read(RPCClient.MAX_FILE_SIZE)

        # Check if the whole file was read
        now = file_descriptor.tell()
        file_descriptor.seek(0, io.SEEK_END)

        if now != file_descriptor.tell():
            raise ValueError("File too large")

        msg_id = self.server_conn.SendMessage(
            spanky_pb2.OutgoingThing(
                channel_id=channel_id,
                source_msg_id=source_msg_id,
                file=spanky_pb2.OutgoingFile(
                    data=buffer,
                    fname=fname,
                ),
            )
        )

        return CMessage.from_id(msg_id, server_id)

    def get_servers(self):
        # Ask for server list
        servers = self.server_conn.GetServerIDs(spanky_pb2.Empty())

        return [CServer.from_id(i) for i in servers.ids]

    @log_call
    def get_server(self, server_id):
        # Ask for server
        return self.server_conn.GetServer(
            spanky_pb2.SomeObjectID(
                id=server_id,
            )
        )

    @log_call
    def get_users(self, server_id):
        return self.server_conn.GetUsers(
            spanky_pb2.SomeObjectID(
                id=server_id,
            )
        )

    @log_call
    def get_role(self, role_id, role_name, server_id):
        # Ask for role
        return self.server_conn.GetRole(
            spanky_pb2.RoleRequest(
                server_id=server_id,
                role_id=role_id,
                role_name=role_name,
            )
        )

    @log_call
    def get_user(self, user_id, user_name, server_id):
        # Ask for user
        return self.server_conn.GetUser(
            spanky_pb2.UserRequest(
                user_id=int(user_id),
                user_name=user_name,
                server_id=server_id,
            )
        )

    @log_call
    def get_attachments(self, message_id, channel_id, server_id):
        return self.server_conn.GetAttachments(
            spanky_pb2.MessageRequest(
                message_id=message_id,
                channel_id=channel_id,
                server_id=server_id,
            )
        )

    @log_call
    def add_roles(self, user_id, server_id, roleid_list):
        """
        Add a list of roles
        """
        return self.server_conn.AddRoles(
            spanky_pb2.RoleAddRem(
                user_id=user_id,
                server_id=server_id,
                roleid_list=roleid_list,
            )
        )

    @log_call
    def remove_roles(self, user_id, server_id, roleid_list):
        """
        Remove a list of roles
        """
        return self.server_conn.RemoveRoles(
            spanky_pb2.RoleAddRem(
                user_id=user_id,
                server_id=server_id,
                roleid_list=roleid_list,
            )
        )

    @log_call
    def send_pm(self, user_id, text):
        """
        Send a PM to user
        """
        pm_id = self.server_conn.SendPM(
            spanky_pb2.OutgoingPM(
                user_id=user_id, msg=spanky_pb2.OutgoingMessage(text=text)
            )
        )

        return pm_id

    @log_call
    def get_channel(self, channel_id, channel_name, server_id):
        # Ask for user
        return self.server_conn.GetChannel(
            spanky_pb2.ChannelRequest(
                channel_id=int(channel_id),
                channel_name=channel_name,
                server_id=server_id,
            )
        )
