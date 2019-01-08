import discord
import logging
import asyncio
import traceback
import random
import collections
from gc import collect

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

client = discord.Client()
bot = None
bot_replies = {}

class Init():
    def __init__(self, bot_inst):
        global client
        global bot
        
        self.client = client

        bot = bot_inst
    
    async def do_init(self):
        await client.login(bot.config["discord_token"])
        await client.connect()

    def get_servers(self):
        servers = []
        for server in client.servers:
            servers.append(Server(server))
            
        return servers
            
    def get_own_id(self):
        return self.client.user.id
    
    def get_bot_roles_in_server(self, server):
        roles = server._raw.get_member(client.user.id).roles
        rlist = []
        
        for r in roles:
            rlist.append(Role(r))
        
        return rlist

class DiscordUtils():
    def str_to_id(self, string):
        return string.replace("@", "").replace("<", "").replace(">", "").replace("!", "").replace("#", "").replace("&", "")

    def id_to_user(self, id_str):
        return "<@%s>" % id_str
    
    def id_to_chan(self, id_str):
        return "<#%s>" % id_str
    
    def id_to_role_name(self, id_str):
        return discord.utils.find(lambda m: m.id == id_str, self.server._raw.roles).name
    
    def user_id_to_name(self, uid):
        return discord.utils.find(lambda m: m.id == uid, self.server._raw.members).name
    
    def user_id_to_object(self, uid):
        return User(discord.utils.find(lambda m: m.id == uid, self.server._raw.members))
    
    def get_channel(self, target, server):
        """
        Returns the target channel
        target can be None, which defaults to the channel from where the message was sent
            a channel name starting with '#' (e.g. #my-channel) or a channel ID
        """
        
        if server:
            target_server = server._raw
        else:
            target_server = self.server._raw
        
        if target:
            if target == -1:
                target = self.source.id
            elif target[0] == "#":
                target = target[1:]
                return discord.utils.find(lambda m: m.name == target, target_server.channels)
            
            return discord.utils.find(lambda m: m.id == target, target_server.channels)
        
    def get_channel_name(self, chan_id):
        chan = discord.utils.find(lambda m: m.id == chan_id, self.server._raw.channels)
        return chan.name
    
    async def async_send_message(self, text, target=-1):
        if target:
            try:
                return Message(await client.send_message(self.get_channel(target), text))
            except:
                print(traceback.format_exc())

    def send_message(self, text, target=-1, server=None):
        async def send_message(channel, message):
            if not channel:
                return
            try:
                if type(self) == EventMessage and self.server.id in bot_replies:
                    old_reply = bot_replies[self.server.id].get_old_reply(self.msg)
                    
                    if old_reply and old_reply._raw.channel.id == channel.id:
                        try:
                            msg = Message(await client.edit_message(old_reply._raw, message))
                        except:
                            print(traceback.format_exc())
                            
                        add_bot_reply(self.server.id, self.msg, msg)
                        return msg
                try:
                    msg = Message(await client.send_message(channel, message))
                except:
                    print(traceback.format_exc())
                    
                if type(self) == EventMessage and msg:
                    add_bot_reply(self.server.id, self.msg._raw, msg)
                return msg
            except:
                print(traceback.format_exc())

        asyncio.run_coroutine_threadsafe(
            send_message(self.get_channel(target, server), text), 
            bot.loop)

    def reply(self, text, target=-1):
        self.send_message("(%s) %s" % (self.author.name, text), target)
        
    def send_file(self, file, target=-1):
        async def send_file(channel, file):
            if self.server.id in bot_replies:
                old_reply = bot_replies[self.server.id].get_old_reply(self.msg)
                if old_reply and old_reply._raw.channel.id == channel.id:
                    
                    try:
                        await client.delete_message(old_reply._raw)
                        msg = Message(await client.send_file(channel, file))
                    except:
                        print(traceback.format_exc())
                    return msg

            try:
                msg = Message(await client.send_file(channel, file))
            except:
                print(traceback.format_exc())
                
            add_bot_reply(self.server.id, self.msg._raw, msg)
            return msg
            
        asyncio.run_coroutine_threadsafe(send_file(self.get_channel(target), file), bot.loop)
        
    async def async_send_file(self, file, target=-1):
        try:
            return Message(await client.send_file(self.get_channel(target), file))
        except:
            print(traceback.format_exc())

class EventPeriodic(DiscordUtils):
    def __init__(self):
        pass

class EventMember(DiscordUtils):
    def __init__(self, event_type, member, member_after=None):
        self.type = event_type
        
        self.member = User(member)
        
        self.server = Server(member.server)
        
        if member_after:
            self.after = EventMember(-1, member_after)
            self.before = EventMember(-1, member)

class EventMessage(DiscordUtils):
    def __init__(self, event_type, message, before=None, deleted=False):
        self.type = event_type
        
        self.msg = Message(message)
        self.channel = Channel(message.channel)
        self.author = User(message.author)
        
        self.server_replies = None
        self.is_pm = False
        if hasattr(message, "server") and message.server:
            self.server = Server(message.server)
            
            if self.server.id in bot_replies:
                self.server_replies = bot_replies[self.server.id]
        else:
            self.is_pm = True
        
        self.source = self.channel
        self.text = self.msg.text
        
        self.do_trigger = True
        
        if before:
            self.before = EventMessage(-1, message=before)
            self.after = EventMessage(-1, message=message)
            self.edited = True
        else:
            self.after = None
            self.edited = False
            
        if deleted:
            self.deleted = True
            # don't trigger hooks on deleted messages
            self.do_trigger = False
        
        self.attachments = []
        if len(message.attachments) > 0:
            for att in message.attachments:
                self.attachments.append(Attachment(att))
        
        self._message = message

class Message():
    def __init__(self, obj):
        self.text = obj.content
        self.id = obj.id
        self.author = User(obj.author)
        self._raw = obj
        
class User():
    def __init__(self, obj):
        self.nick = obj.display_name
        self.name = obj.name
        self.id = obj.id
        self.bot = obj.bot
        
        self.avatar_url = obj.avatar_url
        
        self.roles = []
        if hasattr(obj, "roles"):
            for role in obj.roles:
                if role.name == '@everyone':
                    continue
                self.roles.append(Role(role))
        
        self._raw = obj
        
    def add_role(self, role):
        async def do_add_role(user, role):
            try:
                await client.add_roles(user, role)
            except:
                print(traceback.format_exc())
            
        asyncio.run_coroutine_threadsafe(do_add_role(self._raw, role._raw), bot.loop)
        
    def remove_role(self, role):
        async def do_rem_role(user, role):
            tries = 0
            try:
                while role in user.roles and tries < 5:
                    await client.remove_roles(user, role)
                    tries += 1
            except Exception as e:
                print(e)
            
        asyncio.run_coroutine_threadsafe(do_rem_role(self._raw, role._raw), bot.loop)

    def replace_roles(self, roles):
        async def do_repl_role(user, roles):
            try:
                await client.replace_roles(user, *roles)
            except:
                print(traceback.format_exc())
            
        to_replace = [i._raw for i in roles]
        asyncio.run_coroutine_threadsafe(do_repl_role(self._raw, to_replace), bot.loop)
        
    def kick(self):
        async def do_kick(user):
            try:
                await client.kick(user)
            except:
                print(traceback.format_exc())
        
        asyncio.run_coroutine_threadsafe(do_kick(self._raw), bot.loop)
        
    def ban(self):
        async def do_ban(user):
            try:
                await client.ban(user)
            except:
                print(traceback.format_exc())
        
        asyncio.run_coroutine_threadsafe(do_ban(self._raw), bot.loop)

class Channel():
    def __init__(self, obj):
        self.name = obj.name
        self.id = obj.id
        self._raw = obj
        
    def delete_messages(self, number):
        async def do_delete(channel, num):
            async def del_bulk(channel, num):
                list_del = []
    
                async for m in client.logs_from(channel, limit=num):
                    if not m.pinned:
                        list_del.append(m)
    
                await client.delete_messages(list_del)
    
            async def del_simple(channel, num):
                async for m in client.logs_from(channel, limit=num):
                    if not m.pinned:
                        await client.delete_message(m)
    
            if num > 2 and num < 100:
                try:
                    await del_bulk(channel, num)
                except:
                    await del_simple(channel, num)
            else:
                await del_simple(channel, num)
                
        asyncio.run_coroutine_threadsafe(do_delete(self._raw, number), bot.loop)
        
    async def async_get_latest_messages(self, no_messages):
        msgs = []
        async for msg in client.logs_from(self._raw, limit=no_messages):
            msgs.append(Message(msg))
        
        return msgs
    
class Server():
    def __init__(self, obj):
        self.name = obj.name
        self.id = obj.id
        self._raw = obj
    
    def get_roles(self):
        roles = []
        
        for role in self._raw.roles:
            roles.append(Role(role))

        return roles
        
    def get_role_ids(self):
        ids = []
        for role in self._raw.roles:
            ids.append(role.id)

        return ids
    
    def get_users(self):
        users = []
        
        for user in self._raw.members:
            users.append(User(user))
            
        return users
    
class Role():
    hash = random.randint(0, 2 ** 31)
    
    def __hash__(self):
        return self.hash
        
    def __eq__(self, other):
        if other and self.id == other.id:
            return True
        return False
        
    def __init__(self, obj):
        self.name = obj.name
        self.id = obj.id
        self.position = obj.position
        self._raw = obj
        
class Attachment():
    def __init__(self, obj):
        self.url = obj['url']
        self._raw = obj

class DictQueue():
    def __init__(self, size):
        self.queue = collections.deque(maxlen=size)
    
    def __setitem__(self, key, value):
        self.queue.append((key, value))
        
    def __iter__(self):
        self.index = 0
        return self

    def __next__(self):
        if self.index == len(self.queue):
            raise StopIteration
        
        rval = self.queue[self.index][0]
        self.index = self.index + 1
        return rval
    
    def get_old_reply(self, message):
        for elem in self.queue:
            if elem[0] == message.id:
                return elem[1]
            
        return None
    
def add_bot_reply(server_id, source, reply):
    if server_id not in bot_replies:
        bot_replies[server_id] = DictQueue(100)
    bot_replies[server_id][source.id] = reply
    
    print("%s -> %s" % (source.id, reply.id))

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    bot.ready()

async def call_func(func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except:
        traceback.print_stack()
        traceback.print_exc()

### Messages
@client.event
async def on_message_edit(before, after):
    await call_func(bot.on_message_edit, before, after)

@client.event
async def on_message_delete(message):
    await call_func(bot.on_message_delete, message)

@client.event
async def on_message(message):
    await call_func(bot.on_message, message)
###

### Members
@client.event
async def on_member_join(member):
    await call_func(bot.on_member_join, member)

@client.event
async def on_member_remove(member):
    await call_func(bot.on_member_remove, member)

@client.event
async def on_member_update(before, after):
    await call_func(bot.on_member_update, before, after)

@client.event
async def on_member_ban(member):
    await call_func(bot.on_member_ban, member)

@client.event
async def on_member_unban(server, user):
    await call_func(bot.on_member_unban, server, user)
###


async def periodic_task():
    global plugin_manager
    await client.wait_until_ready()

    while not client.is_closed:
        try:
            bot.on_periodic()
            await asyncio.sleep(0.5)
        except Exception:
            traceback.print_stack()
            traceback.print_exc()
            
client.loop.create_task(periodic_task())