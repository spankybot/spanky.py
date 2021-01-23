import enum
from SpankyCommon.rpc import spanky_pb2

# Base classes that represent objects passed on over the RPC interface
#
# The server/client should extend these classes if needed as this only
# implements serialization according to the proto file


class TransferredObj:
    """
    Implements basic metadata about objects that are passed
    to the clients from the backend.

    These objects can either be passed over GRPC or by reference.
    For example, if implemented over GRPC, it will simply expose the
    raw object received over GRPC, while a 'direct' implementation
    will expose the native object from the framework.
    """

    @property
    def raw(self):
        return self._raw

    @property
    def discord(self):
        if hasattr(self._raw, "_discord"):
            return self._raw._discord
        else:
            raise NotImplementedError(
                "Attribute not available. \
You're probably trying to get the discord object from an over GRPC manager."
            )


class Server(TransferredObj):
    def serialize(self):
        return spanky_pb2.Server(
            id=self._discord.id,
            name=self._discord.name,
            role_ids=[i.id for i in self._discord.roles],
        )


class Role(TransferredObj):
    def serialize(self):
        return spanky_pb2.Role(
            id=self._discord.id,
            name=self._discord.name,
            server_id=self._discord.guild.id,
            managed=self._discord.managed,
            position=self._discord.position,
        )


class Channel(TransferredObj):
    def serialize(self):
        return spanky_pb2.Channel(
            id=self._discord.id,
            name=self._discord.name,
            server_id=self._discord.guild.id,
        )


class User(TransferredObj):
    def serialize(self):
        roles = []
        # Don't return default roles
        for role in self._discord.roles:
            if role.is_default():
                continue
            roles.append(role.id)

        return spanky_pb2.User(
            name=self._discord.name,
            display_name=self._discord.display_name,
            id=self._discord.id,
            joined_at=self.joined_at,
            avatar_url=self.avatar_url,
            premium_since=self.premium_since,
            role_ids=roles,
            server_id=self._discord.guild.id,
        )


class Message(TransferredObj):
    def serialize(self):
        return spanky_pb2.Message(
            content=self.content,
            id=self.id,
            author_name=self.author_name,
            author_id=self.author_id,
            server_id=self.server_id,
            channel_id=self.channel_id,
        )