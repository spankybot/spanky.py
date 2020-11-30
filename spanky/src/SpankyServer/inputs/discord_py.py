# -*- coding: utf-8 -*-

import discord
import logging
import asyncio
import traceback
import io

from SpankyCommon.utils import time_utils as tutils

# from utils import discord_utils as dutils

from SpankyCommon.rpc import rpc_objects as rpcobj

logger = logging.getLogger("discord")
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(
    filename="discord.log", encoding="utf-8", mode="w"
)
handler.setFormatter(
    logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s")
)
logger.addHandler(handler)

# Enable intents god damn it discord
intents = discord.Intents.default()
intents.members = True

allowedMentions = discord.AllowedMentions(
    everyone=False, users=True, roles=True
)

client = discord.Client(intents=intents, allowed_mentions=allowedMentions)
bot = None


class Init:
    def __init__(self, bot_inst):
        global client
        global bot

        self.client = client

        bot = bot_inst

    async def do_init(self):
        await client.login(bot.config["discord_token"])
        await client.connect()

    def get_server_ids(self):
        """
        Get list of servers
        """
        servers = []
        for server in client.guilds:
            servers.append(SServer(server))

        return servers

    def get_server(self, sid):
        return SServer(client.get_guild(sid))

    def get_users(self, server_id):
        """
        Get list of users
        """
        guild = self.client.get_guild(server_id)

        users = []
        for user in guild.members:
            users.append(SUser(user))

        return users

    def get_role(self, role_id, role_name, server_id):
        guild = self.client.get_guild(server_id)

        role = guild.get_role(role_id)
        if not role:
            for srole in guild.roles:
                if srole.name == role_name:
                    role = srole

        if role:
            return SRole(role)

    def get_user(self, user_id, user_name, server_id):
        guild = self.client.get_guild(server_id)

        user = guild.get_member(user_id)
        if not user:
            user = guild.get_member_named(user_name)

        return SUser(user)

    def prepare_embed(
        self,
        title,
        description=None,
        fields=None,
        inline_fields=True,
        image_url=None,
        footer_txt=None,
        thumbnail_url=None,
    ):
        """
        Prepare an embed object
        """
        em = None

        if description:
            em = discord.Embed(title=title, description=description)
        else:
            em = discord.Embed(title=title)

        if fields:
            for el in fields:
                em.add_field(name=el, value=fields[el], inline=inline_fields)

        if image_url:
            em.set_image(url=image_url)

        if footer_txt:
            em.set_footer(text=footer_txt)

        if thumbnail_url:
            em.set_thumbnail(url=thumbnail_url)

        return em

    async def send_file(self, data, fname, channel_id, server_id, source_msg_id):
        server = client.get_guild(server_id)
        chan = server.get_channel(channel_id)

        file_desc = io.BytesIO(data)
        return await chan.send(file=discord.File(file_desc, filename=fname))

    async def send_message(self, text, channel_id, server_id, source_msg_id):
        server = client.get_guild(server_id)
        chan = server.get_channel(channel_id)

        return await chan.send(content=text)

    async def send_embed(self, embed, channel_id, server_id, source_msg_id):
        server = client.get_guild(server_id)
        chan = server.get_channel(channel_id)

        return await chan.send(embed=embed)

    async def get_attachments(self, message_id, channel_id, server_id):
        chan = client.get_channel(channel_id)
        msg = await chan.fetch_message(message_id)

        att_list = []
        for attach in msg.attachments:
            att_list.append(attach.url)

        return att_list

    async def add_roles(self, user_id, server_id, roleid_list):
        server = client.get_guild(server_id)
        user = server.get_member(user_id)

        to_add = []
        for role_id in roleid_list:
            role = server.get_role(role_id)
            if role.managed:
                continue
            to_add.append(role)

        await user.add_roles(*to_add)

    async def remove_roles(self, user_id, server_id, roleid_list):
        server = client.get_guild(server_id)
        user = server.get_member(user_id)

        to_rem = []
        for role_id in roleid_list:
            role = server.get_role(role_id)
            if role.managed or role.is_default():
                continue
            to_rem.append(role)

        await user.remove_roles(*to_rem)

    async def send_pm(self, user_id, text):
        user = client.get_user(user_id)

        return await user.send(content=text)

    async def get_channel(self, channel_id, channel_name, server_id):
        server = client.get_guild(server_id)

        chan = server.get_channel(channel_id)
        if not chan:
            for schan in server.channels:
                if schan.name == channel_name:
                    chan = schan

        if chan:
            return SChannel(chan)


class SServer(rpcobj.Server):
    def __init__(self, obj):
        self._raw = obj
        self.id = obj.id


class SRole(rpcobj.Role):
    def __init__(self, obj):
        self._raw = obj


class SChannel(rpcobj.Channel):
    def __init__(self, obj):
        self._raw = obj


class SUser(rpcobj.User):
    def __init__(self, obj):
        self._raw = obj

        self.joined_at = tutils.datetime_to_ts(obj.joined_at)
        self.avatar_url = str(obj.avatar_url)

        self.premium_since = None
        if obj.premium_since:
            obj.premium_since = tutils.datetime_to_ts(obj.premium_since)


class SMessage(rpcobj.Message):
    def __init__(self, obj):
        self._raw = obj

        self.content = self._raw.content
        self.id = self._raw.id
        self.author_name = self._raw.author.name
        self.author_id = self._raw.author.id
        self.server_id = self._raw.guild.id
        self.channel_id = self._raw.channel.id


@client.event
async def on_ready():
    print("Logged in as")
    print(client.user.name)
    print(client.user.id)
    print("------")
    await bot.ready()


async def call_func(func, *args, **kwargs):
    try:
        await func(*args, **kwargs)
    except:
        traceback.print_stack()
        traceback.print_exc()


# Messages


@client.event
async def on_message_edit(before, after):
    await call_func(bot.on_message_edit, before, after)


@client.event
async def on_message_delete(message):
    await call_func(bot.on_message_delete, message)


@client.event
async def on_bulk_message_delete(messages):
    await call_func(bot.on_bulk_message_delete, messages)


@client.event
async def on_message(message):
    # Don't call on PMs
    if not message.guild:
        return
    await call_func(bot.on_message, SMessage(message))


###

# Members


@client.event
async def on_member_join(member):
    await call_func(bot.on_member_join, member)


@client.event
async def on_member_remove(member):
    await call_func(bot.on_member_remove, member)


@client.event
async def on_member_update(before, after):
    return
    await call_func(bot.on_member_update, before, after)


@client.event
async def on_member_ban(server, member):
    await call_func(bot.on_member_ban, server, member)


@client.event
async def on_member_unban(server, user):
    await call_func(bot.on_member_unban, server, user)


###

# Reactions


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

# Server


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
            await asyncio.sleep(1)
        except Exception:
            traceback.print_stack()
            traceback.print_exc()


client.loop.create_task(periodic_task())
