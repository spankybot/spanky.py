from rpc import spanky_pb2
# Base classes that represent objects passed on over the RPC interface
#
# The server/client should extend these classes if needed as this only
# implements serialization deserialization according to the proto file


class Server():
    def __init__(self, sid, name):
        self.id = sid
        self.name = name

    def serialize(self):
        return spanky_pb2.Server(
            id=self.id,
            name=self.name)

    @classmethod
    def deserialize(cls, obj):
        return cls(
            sid=str(obj.id),
            name=obj.name)


class User():
    def __init__(self, uid, name, display_name):
        self.id = uid
        self.name = name
        self.display_name = display_name

    def serialize(self):
        return spanky_pb2.User(
            name=self.name,
            display_name=self.display_name,
            id=self.id)

    @classmethod
    def deserialize(cls, obj):
        return cls(
            uid=obj.id,
            name=obj.name,
            display_name=obj.display_name)


class Message():
    def __init__(self, content, mid, author, server_id, channel_id):
        self.content = content
        self.id = mid
        self.author = author
        self.server_id = server_id
        self.channel_id = channel_id

    def serialize(self):
        return spanky_pb2.Message(
            content=self.content,
            id=self.id,
            author=self.author.serialize(),
            server_id=self.server_id,
            channel_id=self.channel_id
        )

    @classmethod
    def deserialize(cls, obj):
        return cls(
            content=obj.content,
            message_id=obj.id,
            author=User.deserialize(obj.author),
            server_id=obj.server_id,
            channel_id=obj.channel_id
        )
