from SpankyCommon.rpc import spanky_pb2

# Base classes that represent objects passed on over the RPC interface
#
# The server/client should extend these classes if needed as this only
# implements serialization according to the proto file


class Server:
    def serialize(self):
        return spanky_pb2.Server(
            id=self._raw.id,
            name=self._raw.name,
            role_ids=[i.id for i in self._raw.roles],
        )


class Role:
    def serialize(self):
        return spanky_pb2.Role(
            id=self._raw.id,
            name=self._raw.name,
            server_id=self._raw.guild.id,
            managed=self._raw.managed,
            position=self._raw.position,
        )


class Channel:
    def serialize(self):
        return spanky_pb2.Channel(
            id=self._raw.id,
            name=self._raw.name,
            server_id=self._raw.guild.id
        )


class User:
    def serialize(self):
        roles = []
        # Don't return default roles
        for role in self._raw.roles:
            if role.is_default():
                continue
            roles.append(role.id)

        return spanky_pb2.User(
            name=self._raw.name,
            display_name=self._raw.display_name,
            id=self._raw.id,
            joined_at=self.joined_at,
            avatar_url=self.avatar_url,
            premium_since=self.premium_since,
            role_ids=roles,
            server_id=self._raw.guild.id,
        )


class Message:
    def serialize(self):
        return spanky_pb2.Message(
            content=self.content,
            id=self.id,
            author_name=self.author_name,
            author_id=self.author_id,
            server_id=self.server_id,
            channel_id=self.channel_id,
        )