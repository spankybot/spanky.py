import asyncio
import grpc
import io
import os
import pathlib

from datetime import datetime

from rpc import gen_code
from rpc import spanky_pb2
from rpc import spanky_pb2_grpc
from common.event import EventType

import rpc.rpc_objects as rpcobj

import common.log as log
from utils import bot_utils as butils
from utils import storage

logger = log.botlog("rpc_client", console_level=log.loglevel.DEBUG)

# TODO hack for now
global_cli = None
loop = asyncio.get_event_loop()


class CServer(rpcobj.Server):
    _cache = {}

    def __init__(self):
        self.stor_cache = {}

    @staticmethod
    def from_id(sid):
        new_obj = CServer()

        new_obj._id = sid
        new_obj._raw = None

        new_obj.meta = storage.dsdict(sid, "meta.json")
        CServer._cache[sid] = new_obj

        return new_obj

    @staticmethod
    def from_raw(obj):
        new_obj = CServer()
        new_obj._id = obj.id
        new_obj._raw = obj

        new_obj.meta = storage.dsdict(new_obj._id, "meta.json")
        CServer._cache[new_obj._id] = new_obj

        return new_obj

    @staticmethod
    def connected_servers():
        return CServer._cache.values()

    def fetch_data(self):
        if self._raw is None:
            self._raw = butils.run_async_wait(global_cli.get_server, args=(self._id,))

            self.meta["name"] = self._raw.name
            self.meta["id"] = self._raw.id

    @property
    def id(self):
        return str(self._id)

    @property
    def name(self):
        self.fetch_data()
        return self._raw.name

    @property
    def roles(self):
        self.fetch_data()
        for role_id in self._raw.role_ids:
            yield CRole.from_id(role_id, self._id)

    def get_role(self, role_name=None, role_id=None):
        """
        Get role by name OR ID.
        """
        if role_name and role_id:
            raise ValueError("Don't specify both name and ID")

        return butils.run_async_wait(
            global_cli.get_role, args=(int(role_id), role_name, self._id)
        )

    @staticmethod
    def get_server(server_id):
        # TODO the cache should return copies
        if server_id not in CServer._cache:
            server = butils.run_async_wait(
                global_cli.get_server, args=(server_id,))

            CServer.from_raw(server)

        return CServer._cache[server_id]

    def get_users(self):
        return butils.run_async_wait(global_cli.get_users, args=(self._id,))

    def get_plugin_storage_raw(self, stor_file):
        """
        Get the location of the plugin storage json file
        """
        if self.id + stor_file not in self.stor_cache:
            self.stor_cache[self.id + stor_file] = storage.dsdict(self.id, stor_file)

        return self.stor_cache[self.id + stor_file]

    def get_plugin_storage(self, plugin_fname):
        """
        Get the location of the plugin storage json file
        but with nicer interface
        """
        # Replace paths
        stor_file = plugin_fname.replace(".py", "").replace(os.sep, "_")

        return self.get_plugin_storage_raw(f"{stor_file}.json")

    def get_data_location(self, plugin_fname):
        return os.path.join(storage.DS_LOC, self.id, plugin_fname, "_data/")


class CRole(rpcobj.Role):
    def __init__(self):
        self._role_id = None
        self._server_id = None
        self._raw_obj = None

    @classmethod
    def from_id(cls, role_id, server_id):
        obj = cls()
        obj._role_id = role_id
        obj._server_id = server_id

        return obj

    @classmethod
    def from_raw(cls, obj):
        new_obj = cls()

        new_obj._raw_obj = obj
        new_obj._role_id = obj.id
        new_obj._server_id = obj.server_id

        return new_obj

    @property
    def _raw(self):
        if self._raw_obj is None:
            self._raw_obj = butils.run_async_wait(
                global_cli.get_role, args=(self._role_id, None, self._server_id)
            )

        return self._raw_obj

    @property
    def id(self):
        return str(self._role_id)

    @property
    def name(self):
        return self._raw.name


class CUser(rpcobj.User):
    def __init__(self):
        self._raw_obj = None

    @classmethod
    def from_id(cls, user_id, user_name, server_id):
        new_obj = cls()
        new_obj._raw_obj = None
        new_obj._id = user_id
        new_obj._name = user_name
        new_obj._server_id = server_id

        return new_obj

    @classmethod
    def from_raw(cls, obj):
        new_obj = cls()
        new_obj._raw_obj = obj

        return new_obj

    @property
    def _raw(self):
        if self._raw_obj is None:
            self._raw_obj = butils.run_async_wait(
                global_cli.get_user, args=(self._id, self._server_id)
            )

        return self._raw_obj

    @property
    def id(self):
        return str(self._raw.id)

    @property
    def name(self):
        return self._name

    @property
    def joined_at(self):
        return datetime.fromtimestamp(self._raw.joined_at)

    @property
    def avatar_url(self):
        return self._raw.avatar_url

    @property
    def premium_since(self):
        if self._raw.premium_since:
            return datetime.fromtimestamp(self._raw.premium_since)
        return None

    @property
    def roles(self):
        for role_id in self._raw.role_ids:
            yield CRole.from_id(role_id, self._raw.server_id)


class Resource:
    def __init__(self, url):
        self.url = url


class CMessage(rpcobj.Message):
    def __init__(self):
        self._id = None
        self._raw = None
        self._server_id = None

    @classmethod
    def from_id(cls, msg_id, server_id):
        new_obj = cls()
        new_obj._id = msg_id
        new_obj._server_id = server_id

        return new_obj

    @classmethod
    def from_raw(cls, obj):
        new_obj = cls()
        new_obj._raw = obj
        new_obj._id = obj.id
        new_obj._server_id = obj.server_id

        return new_obj

    @property
    def id(self):
        return self._id

    @property
    def content(self):
        return self._raw.content

    @property
    def channel_id(self):
        return self._raw.channel_id

    @property
    def server(self):
        return CServer.from_id(self._server_id)

    @property
    def author(self):
        return CUser.from_id(
            self._raw.author_id, self._raw.author_name, self.server._id
        )

    @property
    def attachments(self):
        attachments = butils.run_async_wait(
            target=global_cli.get_attachments,
            args=(self._id, self._raw.channel_id, self.server._id),
        )

        for att in attachments.urls:
            yield Resource(att)

    def reply(self, text):
        """
        Reply in the same channel as the given message
        """
        return butils.run_async_wait(
            target=global_cli.send_message,
            kwargs={
                "text": text,
                "channel_id": self._raw.channel_id,
                "server_id": self._server_id,
                "source_msg_id": self._id,
            },
        )

    def send_message(self, text, channel_id):
        return butils.run_async_wait(
            target=global_cli.send_message,
            kwargs={
                "text": text,
                "channel_id": int(channel_id),
                "server_id": self._server_id,
                "source_msg_id": self._id,
            },
        )

    def reply_file(self, file_path=None, fd=None, file_name=None):
        """
        Reply to the message with a file.

        Must specify file_path or fd - file_path has precedence.
        If fd is specified, file_name needs to be set
        """
        if file_path is None and fd is None:
            raise ValueError("Specify either file_path or fd")

        fname = ""
        if file_path:
            fd = io.open(file_path, "rb")
            fname = pathlib.Path(file_path).name
        else:
            fname = file_name

        return butils.run_async_wait(
            target=global_cli.send_file,
            kwargs={
                "file_descriptor": fd,
                "fname": fname,
                "channel_id": self._raw.channel_id,
                "server_id": self._server_id,
                "source_msg_id": self._id,
            },
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
            fields_list.append(spanky_pb2.EmbedField(name=key, text=val))

        butils.run_async(
            global_cli.send_embed,
            kwargs={
                "title": title,
                "description": description,
                "fields": fields_list,
                "inline_fields": inline_fields,
                "image_url": image_url,
                "footer_txt": footer_txt,
                "channel_id": self.channel_id,
                "source_msg_id": self._id,
                "server_id": self._server_id,
            },
        )


class RPCClient:
    MAX_FILE_SIZE = 20 * 1024 * 1024

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
            return evt.event_type, CMessage.from_raw(evt.msg)
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

    async def send_message(self, text, channel_id, server_id, source_msg_id):
        """
        Send a message
        """
        msg_id = await self.server_conn.SendMessage(
            spanky_pb2.OutgoingThing(
                channel_id=channel_id,
                server_id=server_id,
                source_msg_id=source_msg_id,
                msg=spanky_pb2.OutgoingMessage(text=text),
            )
        )

        return CMessage.from_id(msg_id, server_id)

    async def send_embed(
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
        msg_id = await self.server_conn.SendMessage(
            spanky_pb2.OutgoingThing(
                channel_id=channel_id,
                source_msg_id=source_msg_id,
                embed=spanky_pb2.OutgoingEmbed(
                    title=title,
                    description=description,
                    fields=fields,
                    inline_fields=inline_fields,
                    image_url=image_url,
                    footer_txt=footer_txt,
                ),
            )
        )

        return CMessage.from_id(msg_id, server_id)

    async def send_file(
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

        msg_id = await self.server_conn.SendMessage(
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

    async def get_servers(self):
        # Ask for server list
        servers = await self.server_conn.GetServerIDs(spanky_pb2.Empty())

        return [CServer.from_id(i) for i in servers.ids]

    async def get_server(self, server_id):
        # Ask for server
        return await self.server_conn.GetServer(
            spanky_pb2.SomeObjectID(
                id=server_id,
            )
        )

    async def get_users(self, server_id):
        ulist = await self.server_conn.GetUsers(
            spanky_pb2.SomeObjectID(
                id=server_id,
            )
        )

        return [CUser.from_raw(i) for i in ulist.user_list]

    async def get_role(self, role_id, role_name, server_id):
        # Ask for role
        return await self.server_conn.GetRole(
            spanky_pb2.RoleRequest(
                server_id=server_id,
                role_id=role_id,
                role_name=role_name,
            )
        )

    async def get_user(self, user_id, server_id):
        # Ask for user
        return await self.server_conn.GetUserByID(
            spanky_pb2.UserRequest(
                user_id=user_id,
                server_id=server_id,
            )
        )

    async def get_attachments(self, message_id, channel_id, server_id):
        # Ask for user
        return await self.server_conn.GetAttachments(
            spanky_pb2.MessageRequest(
                message_id=message_id,
                channel_id=channel_id,
                server_id=server_id,
            )
        )
