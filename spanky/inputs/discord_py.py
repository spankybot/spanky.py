import discord
import logging
import asyncio
import traceback
import random

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

client = discord.Client()

bot = None

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

class DiscordUtils():
    def str_to_id(self, string):
        return string.replace("@", "").replace("<", "").replace(">", "").replace("!", "").replace("#", "").replace("&", "")

    def id_to_user(self, id_str):
        return "<@%s>" % id_str
    
    def id_to_chan(self, id_str):
        return "<#%s>" % id_str
    
    def get_channel(self, target):
        """
        Returns the target channel
        target can be None, which defaults to the channel from where the message was sent
            a channel name starting with '#' (e.g. #my-channel) or a channel ID
        """
        if target == -1:
            target = self.source.id
        elif target[0] == "#":
            target = target[1:]
            return discord.utils.find(lambda m: m.name == target, self.server._raw.channels)
        
        return discord.utils.find(lambda m: m.id == target, self.server._raw.channels)
    
    def get_channel_name(self, chan_id):
        chan = discord.utils.find(lambda m: m.id == chan_id, self.server._raw.channels)
        return chan.name
    
    async def async_send_message(self, text, target=-1):
        if target:
            return Message(await client.send_message(self.get_channel(target), text))

    def send_message(self, text, target=-1):
        async def send_message(channel, message):
            return Message(await client.send_message(channel, message))

        if target:
            asyncio.run_coroutine_threadsafe(send_message(self.get_channel(target), text), bot.loop)

    def reply(self, text, target=-1):
        self.send_message(text, target)

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
        
        self.server = Server(message.server)
        
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
        
        self._message = message

class Message():
    def __init__(self, obj):
        self.text = obj.content
        self.id = obj.id
        self._raw = obj
        
class User():
    def __init__(self, obj):
        self.nick = obj.display_name
        self.name = obj.name
        self.id = obj.id
        self.bot = obj.bot
        
        self.roles = []
        for role in obj.roles:
            self.roles.append(Role(role))
        
        self._raw = obj

class Channel():
    def __init__(self, obj):
        self.name = obj.name
        self.id = obj.id
        self._raw = obj
    
class Server():
    def __init__(self, obj):
        self.name = obj.name
        self.id = obj.id
        self._raw = obj
        
    def get_role_ids(self):
        ids = []
        for role in self._raw.roles:
            ids.append(role.id)

        return ids
    
class Role():
    hash = random.randint(0, 2 ** 31)
    
    def __hash__(self):
        return self.hash
        
    def __eq__(self, other):
        if self.id == other.id:
            return True
        return False
        
    def __init__(self, obj):
        self.name = obj.name
        self.id = obj.id
        self._raw = obj
        
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