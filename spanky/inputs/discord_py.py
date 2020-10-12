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
from spanky.utils import discord_utils as dutils

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
raw_msg_cache = {} # message cache that we use to map msg_id to msg

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
        for server in client.guilds:
            servers.append(Server(server))

        return servers

    def get_own_id(self):
        return str(self.client.user.id)

    def get_bot_roles_in_server(self, server):
        roles = server._raw.get_member(client.user.id).roles
        rlist = []

        for r in roles:
            rlist.append(Role(r))

        return rlist

    def add_msg_to_cache(self, msg):
        raw_msg_cache[msg.id] = msg

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
        iid_str = None
        try:
            iid_str = int(id_str)
        except ValueError:
            return None

        return discord.utils.find(lambda m: m.id == iid_str, self.get_server()._raw.roles).name

    def user_id_to_name(self, uid):
        iuid = None
        try:
            iuid = int(uid)
        except ValueError:
            return None

        return discord.utils.find(lambda m: m.id == iuid, self.get_server()._raw.members).name

    def user_id_to_object(self, uid):
        iuid = None
        try:
            iuid = int(uid)
        except ValueError:
            return None

        user = discord.utils.find(lambda m: m.id == iuid, self.get_server()._raw.members)
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

            return discord.utils.find(lambda m: m.id == int(target), target_server.channels)

    def get_channel_name(self, chan_id):
        chan = discord.utils.find(lambda m: m.id == int(chan_id), self.get_server()._raw.channels)
        return chan.name

    async def async_edit_message(self, msg, text=None, embed=None):
        if not text and not embed:
            return

        if text:
            await msg._raw.edit(content=text)
        elif embed:
            await msg._raw.edit(embed=embed)

    async def async_send_message(self, text=None, embed=None, target=-1, server=None, timeout=0, check_old=True):
        # Get target, if given
        channel = self.get_channel(target, server)

        # Avoid @here and @everyone
        # TODO remove user ID hack
        if text != None and ("@here" in text or "@everyone" in text):
            await self.async_send_pm("User tried using: `%s` in <#%s> " %
                (text, channel.id), self.user_id_to_object("278247547838136320"))
            return

        # If no target was found, exit
        if not channel:
            return
        try:
            if check_old:
                # Find if this message has been replied to before
                old_reply = None
                if type(self) is EventMessage and self.get_server().id in bot_replies:
                    old_reply = bot_replies[self.get_server().id].get_old_reply(self.msg)

                if type(self) is EventReact and self.get_server().id in bot_replies:
                    old_reply = bot_replies[self.get_server().id].get_bot_message(self.msg)

                # If it was replied within the same channel (no chances of this not being true)
                if old_reply and old_reply._raw.channel.id == channel.id:
                    # Send the message
                    if text != None:
                        await old_reply._raw.edit(content=text)
                    elif embed != None:
                        await old_reply._raw.edit(embed=embed)
                    # Register the bot reply
                    #add_bot_reply(self.get_server().id, self.msg, msg)

                    return Message(old_reply._raw)

            # Send anything that we should send
            if text != None:
                msg = Message(await channel.send(text), timeout)
            elif embed != None:
                msg = Message(await channel.send(text, embed=embed), timeout)

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

    def send_message(self, text, target=-1, server=None, timeout=0):
        asyncio.run_coroutine_threadsafe(
            self.async_send_message(text=text, target=target, server=server, timeout=timeout),
            bot.loop)

    async def async_send_pm(self, text, user):
        await user._raw.send(text)

    def send_pm(self, text, user):
        asyncio.run_coroutine_threadsafe(
            self.async_send_pm(text=text, user=user), bot.loop)

    def send_embed(self, title, description=None, fields=None, inline_fields=True, image_url=None, footer_txt=None, target=-1):
        em = dutils.prepare_embed(title, description, fields, inline_fields, image_url, footer_txt)

        asyncio.run_coroutine_threadsafe(
            self.async_send_message(embed=em, target=target), bot.loop)

    def reply(self, text, target=-1, timeout=0):
        self.send_message("(%s) %s" % (self.author.name, text), target, timeout=timeout)

    def send_file(self, file_path, target=-1, server=None):
        dfile = discord.File(file_path)

        async def send_file(channel, dfile):
            if self.get_server().id in bot_replies:
                old_reply = bot_replies[self.get_server().id].get_old_reply(self.msg)
                if old_reply and old_reply._raw.channel.id == channel.id:

                    try:
                        await channel.delete_messages([old_reply._raw])
                        msg = Message(await channel.send(file=dfile))
                    except:
                        print(traceback.format_exc())
                    add_bot_reply(self.get_server().id, self.msg._raw, msg)
                    return msg

            try:
                msg = Message(await channel.send(file=dfile))
            except:
                print(traceback.format_exc())

            add_bot_reply(self.get_server().id, self.msg._raw, msg)
            return msg

        asyncio.run_coroutine_threadsafe(send_file(self.get_channel(target, server), dfile), bot.loop)

    async def async_send_file(self, file, target=-1):
        try:
            return Message(await self.get_channel(target).send(file=file))
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
        self.server = Server(user.guild)
        self.msg = Message(reaction.message)
        self.channel = Channel(reaction.message.channel)
        self.source = self.channel

        self.reaction = Reaction(reaction)

    def get_server(self):
        return self.server

    def get_msg(self):
        return self.msg

class EventMember(DiscordUtils):
    def __init__(self, event_type, member, member_after=None):
        self.type = event_type
        self.member = User(member)
        self.server = Server(member.guild)

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
        if hasattr(message, "guild") and message.guild:
            self.server = Server(message.guild)

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
            yield Attachment(att).url
            return

        for emb in self.embeds:
            yield Embed(emb).url
            return

        if self.user_id_to_object(stripped) != None:
            yield str(self.user_id_to_object(stripped).avatar_url)
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
                if self.channel.id != str(reply._raw.channel.id):
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
        self.id = str(obj.id)
        self.author = User(obj.author)
        self.clean_content = obj.clean_content
        self._raw = obj

        # Delete the message `timeout` seconds after it was created
        self.timeout = timeout

    def reactions(self):
        for react in self._raw.reactions:
            yield Reaction(react)

    @property
    def created_at(self):
        return self._raw.created_at.timestamp()

    @property
    def channel(self):
        return Channel(self._raw.channel)

    async def async_add_reaction(self, string):
        try:
            await self._raw.add_reaction(string)
        except:
            traceback.print_exc()

    async def async_remove_reaction(self, string, author):
        try:
            await self._raw.remove_reaction(string, author._raw)
        except:
            traceback.print_exc()

    def add_reaction(self, string):
        asyncio.run_coroutine_threadsafe(self.async_add_reaction(string), bot.loop)

    def delete_message(self):
        async def delete_message(message):
            await self._raw.delete()
        asyncio.run_coroutine_threadsafe(delete_message(self._raw), bot.loop)

    async def clear_reactions(self):
        await self._raw.clear_reactions()

class User():
    def __init__(self, obj):
        self.nick = obj.display_name
        self.name = obj.name
        self.id = str(obj.id)
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
                await self._raw.add_roles(role)
            except:
                print(traceback.format_exc())

        asyncio.run_coroutine_threadsafe(do_add_role(self._raw, role._raw), bot.loop)

    def remove_role(self, role):
        async def do_rem_role(user, role):
            tries = 0
            try:
                while role in user.roles and tries < 5:
                    await self._raw.remove_roles(role)
                    tries += 1
            except Exception as e:
                print(e)

        asyncio.run_coroutine_threadsafe(do_rem_role(self._raw, role._raw), bot.loop)

    def replace_roles(self, roles):
        async def do_repl_role(user, roles):
            try:
                nitro = None
                if self._raw.premium_since:
                    # get nitro role
                    for role in self.roles:
                        if role.name == "Nitro Booster":
                            nitro = role._raw

                    found = False
                    for erole in roles:
                        if erole.id == nitro.id:
                            found = True
                            break
                    if not found:
                        roles.append(nitro)

                await self._raw.edit(roles=roles)
            except:
                print(traceback.format_exc())

        to_replace = [i._raw for i in roles]
        asyncio.run_coroutine_threadsafe(do_repl_role(self._raw, to_replace), bot.loop)

    def kick(self):
        async def do_kick(user):
            try:
                await user.kick()
            except:
                print(traceback.format_exc())

        asyncio.run_coroutine_threadsafe(do_kick(self._raw), bot.loop)

    def ban(self, server):
        async def do_ban(user):
            try:
                await server._raw.ban(user, delete_message_days=0)
            except:
                print(traceback.format_exc())

        asyncio.run_coroutine_threadsafe(do_ban(self._raw), bot.loop)

    def unban(self, server):
        async def do_unban(user, server):
            try:
                await server._raw.unban(user)
            except:
                print(traceback.format_exc())

        asyncio.run_coroutine_threadsafe(do_unban(self._raw, server), bot.loop)

    def send_pm(self, text):
        async def async_send_pm(text):
            await self._raw.send(text)

        asyncio.run_coroutine_threadsafe(
            async_send_pm(text=text), bot.loop)

class Channel():
    def __init__(self, obj):
        self.name = None
        if hasattr(obj, "name"):
            self.name = obj.name

        self.id = str(obj.id)
        self.position = None
        if hasattr(obj, "position"):
            self.position = obj.position

        self.server = None
        if hasattr(obj, "guild"):
            self.server = Server(obj.guild)

        self.topic = None
        if hasattr(obj, "topic"):
            self.topic = obj.topic

        self.is_nsfw = None
        if hasattr(obj, "is_nsfw"):
            self.is_nsfw = obj.is_nsfw()
        self._raw = obj

    def delete_messages(self, number):
        async def do_delete(channel, num):
            async def del_bulk(channel, num):
                list_del = []

                async for m in self._raw.history(limit=num):
                    if not m.pinned:
                        list_del.append(m)

                await self._raw.delete_messages(list_del)

            async def del_simple(channel, num):
                async for m in self._raw.history(limit=num):
                    if not m.pinned:
                        await m.delete()

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
        async for msg in self._raw.history(limit=no_messages):
            msgs.append(Message(msg))

        return msgs

    async def async_get_message(self, msg_id):
        return Message(await self._raw.fetch_message(msg_id))

    async def set_position(self, position):
        await self._raw.edit(position=position)

    async def move_to_category(self, cat_id, sync_permissions=True):
        cat = self.server.find_category_by_id(cat_id)
        await self._raw.edit(category=cat._raw, sync_permissions=sync_permissions)

    def set_topic(self, text):
        async def set_topic(text):
            await self._raw.edit(topic=text)

        asyncio.run_coroutine_threadsafe(set_topic(text), bot.loop)

    def set_nsfw(self, state):
        async def set_nsfw(state):
            await self._raw.edit(nsfw=state)

        asyncio.run_coroutine_threadsafe(set_nsfw(state), bot.loop)

    def members_accessing_chan(self):
        for user in self._raw.members:
            yield User(user)

    def get_user_overwrites(self):
        for thing, overwrite in self._raw.overwrites.items():
            if type(thing) == discord.Member:
                yield User(thing), PermOverwrite(overwrite)

    async def set_user_overwrite(self, user, **perms):
        await self._raw.set_permissions(
            user._raw,
            **perms)

    async def remove_user_overwrite(self, user):
        await self._raw.set_permissions(
            user._raw, overwrite=None)

class PermOverwrite():
    def __init__(self, obj):
        self._raw = obj



class Category():
    def __repr__(self):
        return self.name

    def __init__(self, obj):
        self._raw = obj
        self.name = obj.name
        self.id = obj.id

    @property
    def channels(self):
        for chan in self._raw.channels:
            yield Channel(chan)

class Server():
    def __init__(self, obj):
        self.name = obj.name
        self.id = str(obj.id)
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
        bans = await self._raw.bans()

        ulist = []
        for entry in bans:
            ulist.append(User(entry.user))

        return ulist

    def get_categories(self):
        for cat in self._raw.categories:
            yield Category(cat)

    def find_category_by_name(self, name):
        for cat in self._raw.categories:
            if cat.name.lower() == name.lower():
                return cat

        return None

    def find_category_by_id(self, id):
        for cat in self._raw.categories:
            if str(cat.id) == str(id):
                return Category(cat)

        return None

    async def create_text_channel(self, name, cat_id):

        cat = self.find_category_by_id(cat_id)
        if not cat:
            print("Could not find category %s" % cat_id)

        return Channel(await self._raw.create_text_channel(name, category=cat._raw))

    async def delete_channel(self, chan):
        await chan._raw.delete()

    def get_chans_in_cat(self, cat_id):
        cat = self.find_category_by_id(cat_id)

        for chan in cat.channels:
            yield chan

    async def create_role(self, name, mentionable=False):
        existing = None
        for crtrole in self.get_roles():
            if crtrole.name == name:
                existing = crtrole

        created = None
        if not existing:
            created = await self._raw.create_role(
                name=name,
                mentionable=mentionable)
        else:
            created = existing._raw
            await created.edit(mentionable=mentionable)

        return Role(created)

    async def delete_role_by_name(self, role_name):
        for role in self._raw.roles:
            if role.name == role_name:
                await role.delete()

        print("Could not find role %s to delete" % role_name)

    @property
    def banner_url(self):
        return self._raw.banner_url

    async def set_banner(self, data):
        await self._raw.edit(banner=data)

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
        self.id = str(obj.id)
        self.position = obj.position
        self._raw = obj

    async def set_position(self, position):
        await self._raw.edit(position=position)

    def set_name(self, name):
        async def set_name(name):
            await self._raw.edit(name=name)

        asyncio.run_coroutine_threadsafe(set_name(name), bot.loop)

class Attachment():
    def __init__(self, obj):
        self.url = obj.url
        self._raw = obj

class Embed():
    def __init__(self, obj):
        self.url = obj.url
        self._raw = obj

class Reaction():
    def __init__(self, obj):
        self.emoji = Emoji(obj.emoji)

        self.count = 1
        if hasattr(obj, "count"):
            self.count = obj.count

        self._raw = obj

    async def users(self):
        async for user in self._raw.users():
            yield User(user)

    async def remove(self, user):
        await self._raw.remove(user._raw)

class Emoji():
    def __init__(self, obj):
        if isinstance(obj, str):
            self.name = obj
            self.id = None
            self.url = None
        else:
            self.name = obj.name
            self.id = str(obj.id)
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

        if message.id in raw_msg_cache:
            return raw_msg_cache[message.id]

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
    bot_replies[server_id][str(source.id)] = reply

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
async def on_member_ban(server, member):
    await call_func(bot.on_member_ban, server, member)

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

@client.event
async def on_raw_reaction_add(reaction):
    if reaction.member.id != client.user.id:
        msg_id = str(reaction.message_id)
        if msg_id not in raw_msg_cache:
            return

        # push in stuff into the reaction object
        # TODO: don't override things
        reaction.message = raw_msg_cache[msg_id]._raw
        reaction.channel = raw_msg_cache[msg_id]._raw.channel

        await call_func(bot.on_reaction_add, reaction, reaction.member)
###

### Server
@client.event
async def on_server_join(server):
    await call_func(bot.on_server_join, server)

async def on_server_remove(server):
    await call_func(bot.on_server_leave, server)

###

async def periodic_task():
    await client.wait_until_ready()

    while not client.is_closed():
        try:
            bot.on_periodic()
            check_to_delete()
            await asyncio.sleep(1)
        except Exception:
            traceback.print_stack()
            traceback.print_exc()

client.loop.create_task(periodic_task())
