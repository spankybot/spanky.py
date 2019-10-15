#-*- coding: utf-8 -*-

import discord
import logging
import asyncio
import traceback
import random
import collections
import requests
import json
import abc
from gc import collect
from spanky.utils.image import Image
from spanky.utils import time_utils

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

client = discord.Client()
bot = None
bot_replies = {}
to_delete = {}
emojis = json.load(open("plugin_data/twemoji_800x800.json"))

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

class DiscordUtils(abc.ABC):
    @abc.abstractmethod
    def get_server(self):
        pass

    @abc.abstractmethod
    def get_msg(self):
        pass

    def str_to_id(self, string):
        return string.strip().replace("@", "").replace("<", "").replace(">", "").replace("!", "").replace("#", "").replace("&", "").replace(":", " ")

    def id_to_user(self, id_str):
        return "<@%s>" % id_str

    def id_to_chan(self, id_str):
        return "<#%s>" % id_str

    def id_to_role_name(self, id_str):
        return discord.utils.find(lambda m: m.id == id_str, self.get_server()._raw.roles).name

    def user_id_to_name(self, uid):
        return discord.utils.find(lambda m: m.id == uid, self.get_server()._raw.members).name

    def user_id_to_object(self, uid):
        user = discord.utils.find(lambda m: m.id == uid, self.get_server()._raw.members)
        if user:
            return User(user)
        else:
            return None

    async def async_set_game_status(self, game_status):
        await client.change_presence(game=discord.Game(name=game_status))

    def get_channel(self, target, server):
        """
        Returns the target channel
        target can be None, which defaults to the channel from where the message was sent
            a channel name starting with '#' (e.g. #my-channel) or a channel ID
        """

        if server:
            target_server = server._raw
        else:
            target_server = self.get_server()._raw

        if target:
            if target == -1:
                target = self.source.id
            elif target[0] == "#":
                target = target[1:]
                return discord.utils.find(lambda m: m.name == target, target_server.channels)

            return discord.utils.find(lambda m: m.id == target, target_server.channels)

    def get_channel_name(self, chan_id):
        chan = discord.utils.find(lambda m: m.id == chan_id, self.get_server()._raw.channels)
        return chan.name

    async def async_send_message(self, text=None, embed=None, target=-1, server=None, timeout=0):
        # Get target, if given
        channel = self.get_channel(target, server)

        # Avoid @here and @everyone
        try:
            if text != None and ("@here" in text or "@everyone" in text):
                await self.async_send_pm("User tried using: `%s` in <#%s> " %
                    (text, channel.id), self.user_id_to_object("278247547838136320"))
                return
        except:
            traceback.print_exc()

        # If no target was found, exit
        if not channel:
            return
        try:

            # Find if this message has been replied to before
            old_reply = None
            if type(self) is EventMessage and self.get_server().id in bot_replies:
                old_reply = bot_replies[self.get_server().id].get_old_reply(self.msg)

            if type(self) is EventReact and self.get_server().id in bot_replies:
                old_reply = bot_replies[self.get_server().id].get_bot_message(self.msg)

            # If it was replied within the same channel as now (not chances of this not being true)
            if old_reply and old_reply._raw.channel.id == channel.id:
                try:
                    # Send the message
                    msg = Message(await client.edit_message(old_reply._raw, text), timeout)
                    # Register the bot reply
                    add_bot_reply(self.get_server().id, self.msg, msg)

                    return msg
                except:
                    print(traceback.format_exc())
                    return
            try:
                # Send anything that we should send
                if text != None:
                    msg = Message(await client.send_message(channel, text), timeout)
                elif embed != None:
                    msg = Message(await client.send_message(channel, embed=embed), timeout)

                # Add the bot reply
                if msg:
                    if type(self) is EventMessage:
                        add_bot_reply(self.get_server().id, self.msg._raw, msg)
                    else:
                        # Add a temporary reply that will be self-deleted after a timeout
                        add_temporary_reply(msg)

                return msg
            except:
                print(traceback.format_exc())

        except:
            print(traceback.format_exc())

    def send_message(self, text, target=-1, server=None, timeout=0):
        asyncio.run_coroutine_threadsafe(
            self.async_send_message(text=text, target=target, server=server, timeout=timeout),
            bot.loop)

    async def async_send_pm(self, text, user):
        await client.send_message(user._raw, text)

    def send_pm(self, text, user):
        asyncio.run_coroutine_threadsafe(
            self.async_send_pm(text=text, user=user), bot.loop)

    def send_embed(self, title, description, fields, target=-1):
        em = discord.Embed(title=title, description=description)
        for el in fields:
            em.add_field(name=el, value=fields[el])

        asyncio.run_coroutine_threadsafe(
            self.async_send_message(embed=em, target=target), bot.loop)

    def reply(self, text, target=-1, timeout=0):
        self.send_message("(%s) %s" % (self.author.name, text), target, timeout=timeout)

    def send_file(self, file, target=-1, server=None):
        async def send_file(channel, file):
            if self.get_server().id in bot_replies:
                old_reply = bot_replies[self.get_server().id].get_old_reply(self.msg)
                if old_reply and old_reply._raw.channel.id == channel.id:

                    try:
                        await client.delete_message(old_reply._raw)
                        msg = Message(await client.send_file(channel, file))
                    except:
                        print(traceback.format_exc())
                    add_bot_reply(self.get_server().id, self.msg._raw, msg)
                    return msg

            try:
                msg = Message(await client.send_file(channel, file))
            except:
                print(traceback.format_exc())

            add_bot_reply(self.get_server().id, self.msg._raw, msg)
            return msg

        asyncio.run_coroutine_threadsafe(send_file(self.get_channel(target, server), file), bot.loop)

    async def async_send_file(self, file, target=-1):
        try:
            return Message(await client.send_file(self.get_channel(target), file))
        except:
            print(traceback.format_exc())

    async def async_set_avatar(self, image):
        await client.edit_profile(avatar=image)

class EventPeriodic(DiscordUtils):
    def __init__(self):
        pass

    def get_server(self):
        return None

    def get_msg(self):
        return None

class EventReact(DiscordUtils):
    def __init__(self, event_type, user, reaction):
        self.type = event_type
        self.author = User(user)
        self.server = Server(user.server)
        self.msg = Message(reaction.message)
        self.channel = Channel(reaction.message.channel)

        self.reaction = Reaction(reaction)

    def get_server(self):
        return self.server

    def get_msg(self):
        return self.msg

class EventMember(DiscordUtils):
    def __init__(self, event_type, member, member_after=None):
        self.type = event_type
        self.member = User(member)
        self.server = Server(member.server)

        if member_after:
            self.after = EventMember(-1, member_after)
            self.before = EventMember(-1, member)

    def get_server(self):
        return self.server

    def get_msg(self):
        return None

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
            self.before = None
            self.after = None
            self.edited = False

        if deleted:
            self.deleted = True
            # don't trigger hooks on deleted messages
            self.do_trigger = False

        self._message = message

    def get_server(self):
        return self.server

    def get_msg(self):
        return self.msg

    @property
    def attachments(self):
        for att in self._message.attachments:
            yield Attachment(att)

    @property
    def embeds(self):
        for emb in self._message.embeds:
            yield Embed(emb)

    @property
    def image(self):
        for url in self.url:
            yield Image(url)

    @property
    def url(self):
        def strip_url(text):
            return text.replace("<", "").replace(">", "")

        last_word = self.text.split()[-1]

        stripped = self.str_to_id(last_word).split()[-1]

        for att in self.attachments:
            yield att.url
            return

        for emb in self.embeds:
            yield emb.url
            return

        if self.user_id_to_object(stripped) != None:
            yield self.user_id_to_object(stripped).avatar_url
            return
        elif len(stripped) == 1 and format(ord(stripped), "x") in emojis:
            yield emojis[format(ord(stripped), "x")]
            return
        elif requests.get("https://cdn.discordapp.com/emojis/%s.gif" % stripped).status_code == 200:
            yield "https://cdn.discordapp.com/emojis/%s.gif" % stripped
            return
        elif requests.get("https://cdn.discordapp.com/emojis/%s.png" % stripped).status_code == 200:
            yield "https://cdn.discordapp.com/emojis/%s.png" % stripped
            return
        elif last_word.startswith("http"):
            yield strip_url(last_word)
            return
        elif self.server.id in bot_replies:
            for reply in bot_replies[self.server.id].bot_messages():

                if self.channel.id != reply._raw.channel.id:
                    continue

                for att in reply._raw.attachments:
                    print(att)
                    yield Attachment(att).url
                    return

                for emb in reply._raw.embeds:
                    print(emb)
                    yield Embed(emb).url
                    return

                if strip_url(reply.text.split()[-1]).startswith("http"):
                    yield strip_url(reply.text.split()[-1])
                    return

class Message():
    def __init__(self, obj, timeout=0):
        self.text = obj.content
        self.id = obj.id
        self.author = User(obj.author)
        self.clean_content = obj.clean_content
        self._raw = obj

        # Delete the message `timeout` seconds after it was created
        self.timeout = timeout

    async def async_add_reaction(self, string):
        try:
            await client.add_reaction(self._raw, string)
        except:
            traceback.print_exc()

    async def async_remove_reaction(self, string, author):
        try:
            await client.remove_reaction(self._raw, string, author._raw)
        except:
            traceback.print_exc()

    def delete_message(self):
        async def delete_message(message):
            await client.delete_message(message)
        asyncio.run_coroutine_threadsafe(delete_message(self._raw), bot.loop)

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
                await client.ban(user, delete_message_days=0)
            except:
                print(traceback.format_exc())

        asyncio.run_coroutine_threadsafe(do_ban(self._raw), bot.loop)

    def unban(self, server):
        async def do_unban(user, server):
            try:
                await client.unban(server, user)
            except:
                print(traceback.format_exc())

        asyncio.run_coroutine_threadsafe(do_unban(self._raw, server), bot.loop)

class Channel():
    def __init__(self, obj):
        self.name = obj.name
        self.id = obj.id
        self.position = obj.position
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

    async def async_get_message(self, msg_id):
        return Message(await client.get_message(self._raw, msg_id))

    def move_channel(self, position):
        async def move_channel(channel, position):
            try:
                await client.move_channel(channel, position)
            except:
                print(traceback.format_exc())

        asyncio.run_coroutine_threadsafe(move_channel(self._raw, position), bot.loop)

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

    def get_channels(self):
        chans = []

        for chan in self._raw.channels:
            chans.append(Channel(chan))

        return chans

    async def get_bans(self):
        bans = await client.get_bans(self._raw)

        ulist = []
        for user in bans:
            ulist.append(User(user))

        return ulist

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

class Embed():
    def __init__(self, obj):
        self.url = obj['url']
        self._raw = obj

class Reaction():
    def __init__(self, obj):
        self.emoji = Emoji(obj.emoji)
        self._raw = obj

class Emoji():
    def __init__(self, obj):
        if isinstance(obj, str):
            self.name = obj
            self.id = None
            self.url = None
        else:
            self.name = obj.name
            self.id = obj.id
            self.url = obj.url

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

    def get_bot_message(self, message):
        for elem in self.queue:
            if elem[1].id == message.id:
                return elem[1]

        return None

    def bot_messages(self):
        for elem in reversed(self.queue):
            yield elem[1]

def add_temporary_reply(reply):
    if reply.timeout != 0:
        to_delete[time_utils.tnow() + reply.timeout] = reply

def add_bot_reply(server_id, source, reply):
    if server_id not in bot_replies:
        bot_replies[server_id] = DictQueue(20)
    bot_replies[server_id][source.id] = reply

    if reply.timeout != 0:
        print("Add timeout message in " + str(reply.timeout))
        add_temporary_reply(reply)

    print("%s -> %s" % (source.id, reply.id))

def check_to_delete():
    for key in list(to_delete.keys()):
        if key < time_utils.tnow():
            to_delete[key].delete_message()
            del to_delete[key]

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

### Reactions
@client.event
async def on_reaction_add(reaction, user):
    if user.id != client.user.id:
        await call_func(bot.on_reaction_add, reaction, user)

async def on_reaction_remove(reaction, user):
    if user.id != client.user.id:
        await call_func(bot.on_reaction_remove, reaction, user)
###

### Server
@client.event
async def on_server_join(server):
    await call_func(bot.on_server_join, server)

async def on_server_remove(server):
    await call_func(bot.on_server_leave, server)

###

async def periodic_task():
    global plugin_manager
    await client.wait_until_ready()

    while not client.is_closed:
        try:
            bot.on_periodic()
            check_to_delete()
            await asyncio.sleep(1)
        except Exception:
            traceback.print_stack()
            traceback.print_exc()

client.loop.create_task(periodic_task())
