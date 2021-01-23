import io
import os
import pathlib

from datetime import datetime

import SpankyCommon.rpc.rpc_objects as rpcobj

from SpankyCommon.utils import log
from SpankyCommon.event import EventType
from SpankyCommon.utils import storage

from SpankyWorker.utils import image

logger = log.botlog("rpc_client", console_level=log.loglevel.DEBUG)

server_comm = None


def set_server_comm(comm_object):
    """
    Set what backend to use to talk to the server
    """
    global server_comm
    server_comm = comm_object


def get_server_comm():
    """
    Get what backend to use to talk to the server
    """
    return server_comm


class CGeneric:
    @staticmethod
    def connect(*args, **kwargs):
        return server_comm.connect(*args, **kwargs)

    @staticmethod
    def set_command_list(*args, **kwargs):
        return server_comm.set_command_list(*args, **kwargs)

    @staticmethod
    def get_event(*args, **kwargs):
        evt_type, payload = server_comm.get_event(*args, **kwargs)

        if evt_type == EventType.message:
            return ((evt_type, CMessage.from_raw(payload)),)
        elif evt_type == EventType.on_ready:
            return ((evt_type, None),)

    @staticmethod
    def send_message(*args, **kwargs):
        return server_comm.send_message(*args, **kwargs)

    @staticmethod
    def get_servers(*args, **kwargs):
        return server_comm.get_servers(*args, **kwargs)

    @staticmethod
    def get_bot_id(*args, **kwargs):
        return server_comm.get_bot_id(*args, **kwargs)


class StorageSystem:
    stor_cache = {}

    @staticmethod
    def get_storage_from_cache(parent, stor_file):
        """
        Get the location of the plugin storage json file
        """
        # If not in cache, create it
        if parent + stor_file not in StorageSystem.stor_cache:
            StorageSystem.stor_cache[parent + stor_file] = storage.dsdict(
                parent, stor_file
            )

        return StorageSystem.stor_cache[parent + stor_file]

    @staticmethod
    def get_unique_storage(plugin_fname):
        # Replace paths
        stor_file = plugin_fname.replace(".py", "").replace(os.sep, "_")

        return StorageSystem.get_storage_from_cache(
            "unique", f"{stor_file}.json")


class CServer(rpcobj.Server):
    _cache = {}

    def __init__(self):
        pass

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
            self._raw = server_comm.get_server(self._id)

            self.meta["name"] = self._raw.name
            self.meta["id"] = self._raw.id

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        self.fetch_data()
        return self._raw.name

    @property
    def roles(self):
        self.fetch_data()
        for role_id in self._raw.role_ids:
            yield CRole.from_id(role_id, self._id)

    def get_role(self, role_id=None, role_name=None):
        """
        Get role by name OR ID.
        """
        if role_name and role_id:
            raise ValueError("Don't specify both name and ID")

        if not role_name and not role_id:
            raise ValueError("Specify one of name or ID")

        resp = server_comm.get_role(
            role_id=int(role_id), role_name=role_name, server_id=self._id
        )

        return CRole.from_raw(resp)

    @staticmethod
    def get_server(server_id):
        if server_id not in CServer._cache:
            # Get requested server by ID if possible
            server = server_comm.get_server(server_id)
            CServer.from_raw(server)

        return CServer._cache[server_id]

    def get_users(self):
        resp = server_comm.get_users(self._id)

        for user in resp.user_list:
            yield CUser.from_raw(user)

    def get_user(self, user_id=None, user_name=None):
        if user_id and user_name:
            raise ValueError("Specify only one of user_id or user_name")
        elif not user_id and not user_name:
            raise ValueError("Specify one of user_id or user_name")

        resp = server_comm.get_user(
            int(user_id),
            user_name,
            self._id,
        )

        return CUser.from_raw(resp)

    def get_plugin_storage_raw(self, stor_file):
        """
        Get the location of the plugin storage json file
        """
        return StorageSystem.get_storage_from_cache(str(self.id), stor_file)

    def get_plugin_storage(self, plugin_fname):
        """
        Get the location of the plugin storage json file
        but with nicer interface
        """
        # Replace paths
        stor_file = plugin_fname.replace(".py", "").replace(os.sep, "_")

        return self.get_plugin_storage_raw(f"{stor_file}.json")

    def get_data_location(self, plugin_fname):
        return os.path.join(storage.DS_LOC, str(self.id), plugin_fname, "_data/")

    def get_channel(self, channel_id=None, channel_name=None):
        if channel_name and channel_id:
            raise ValueError("Don't specify both name and ID")

        if not channel_name and not channel_id:
            raise ValueError("Specify one of name or ID")

        resp = server_comm.get_channel(
            int(channel_id),
            channel_name,
            self._id,
        )

        return CChannel.from_raw(resp)


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
            self._raw_obj = server_comm.get_role(
                self._role_id, None, self._server_id
            )

        return self._raw_obj

    @property
    def id(self):
        return self._role_id

    @property
    def name(self):
        return self._raw.name

    @property
    def managed(self):
        return self._raw.managed


class CChannel(rpcobj.Channel):
    def __init__(self):
        self._channel_id = None
        self._server_id = None
        self._raw_obj = None

    @classmethod
    def from_id(cls, channel_id, server_id):
        obj = cls()
        obj._channel_id = channel_id
        obj._server_id = server_id

        return obj

    @classmethod
    def from_raw(cls, obj):
        new_obj = cls()
        new_obj._raw_obj = obj
        new_obj._channel_id = obj.id
        new_obj._server_id = obj.server_id

        return new_obj

    @property
    def _raw(self):
        if self._raw_obj is None:
            self._raw_obj = server_comm.get_channel(
                self._channel_id, None, self._server_id
            )

        return self._raw_obj

    @property
    def id(self):
        return self._channel_id

    @property
    def name(self):
        return self._raw.name

    def get_messages(self, count, before_ts=None, after_ts=None):
        server_comm.get_messages(
            count, before_ts, after_ts, self._channel_id, self._server_id
        )


class CUser(rpcobj.User):
    def __init__(self):
        self._raw_obj = None
        self._id = None
        self._name = None
        self._server_id = None

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
        new_obj._id = obj.id
        new_obj._name = obj.name
        new_obj._server_id = obj.server_id

        return new_obj

    @property
    def _raw(self):
        if self._raw_obj is None:
            self._raw_obj = server_comm.get_user(
                self._id, self._name, self._server_id
            )

        return self._raw_obj

    @property
    def id(self):
        return self._id

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

    def replace_roles(self, role_list):
        """
        Replace user roles with new roles
        """
        # Remove non premium roles
        to_remove = []
        for role in self.roles:
            if role.managed:
                continue

            to_remove.append(int(role.id))

        if len(to_remove) > 0:
            server_comm.remove_roles(self._id, self._server_id, to_remove)

        # Add roles
        server_comm.add_roles(
            self._id, self._server_id, [int(i.id) for i in role_list]
        )

    def add_role(self, role):
        server_comm.add_roles(self._id, self._server_id, [int(role.id)])

    def remove_role(self, role):
        server_comm.remove_roles(self._id, self._server_id, [int(role.id)])

    def send_pm(self, content):
        return server_comm.send_pm(self._id, content)


class Resource(image.Image):
    def __init__(self, url):
        super().__init__(url=url)


class CMessage(rpcobj.Message):
    def __init__(self):
        self._id = None
        self._raw = None
        self._server_id = None
        self._author_id = None

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
        new_obj._author_id = obj.author_id

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
    def author_id(self):
        if self._author_id:
            return self._author_id
        else:
            return CUser.from_id(
                self._raw.author_id, self._raw.author_name, self.server._id
            ).id

    @property
    def author(self):
        return CUser.from_id(
            self._raw.author_id, self._raw.author_name, self.server._id
        )

    @property
    def attachments(self):
        attachments = server_comm.get_attachments(
            self._id, self._raw.channel_id, self.server._id
        )

        for att in attachments.urls:
            yield Resource(att)

    def reply(self, text):
        """
        Reply in the same channel as the given message
        """
        server_comm.send_message(
            text=text,
            channel_id=self._raw.channel_id,
            server_id=self._server_id,
            source_msg_id=self._id,
        )

    def send_message(self, text, channel_id):
        server_comm.send_message(
            text=text,
            channel_id=int(channel_id),
            server_id=self._server_id,
            source_msg_id=self._id,
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

        server_comm.send_file(
            file_descriptor=fd,
            fname=fname,
            channel_id=self._raw.channel_id,
            server_id=self._server_id,
            source_msg_id=self._id,
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
        server_comm.send_embed(
            title=title,
            description=description,
            fields=fields,
            inline_fields=inline_fields,
            image_url=image_url,
            footer_txt=footer_txt,
            channel_id=self._raw.channel_id,
            source_msg_id=self._id,
            server_id=self._server_id,
        )

    def delete_message(self):
        server_comm.delete_message(
            message_id=self._id,
            channel_id=self._raw.channel_id,
            server_id=self._server_id,
        )

    def add_reaction(self, reaction):
        server_comm.add_reaction(
            message_id=self._id,
            channel_id=self._raw.channel_id,
            server_id=self._server_id,
            reaction=reaction
        )

    def remove_reaction(self, reaction):
        # server_comm.add_reaction(
        #     msg_id=self._id,
        #     reaction=reaction
        # )
        pass