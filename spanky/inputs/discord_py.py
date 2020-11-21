# -*- coding: utf-8 -*-

import discord
import logging
import asyncio
import traceback
import random
import collections
import requests
import json
import abc
import io

from gc import collect
from utils import time_utils as tutils

# from utils import discord_utils as dutils

import rpc.rpc_objects as rpcobj

logger = logging.getLogger("discord")
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
handler.setFormatter(
    logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s")
)
logger.addHandler(handler)

# Enable intents god damn it discord
intents = discord.Intents.default()
intents.members = True

allowedMentions = discord.AllowedMentions(everyone=False, users=True, roles=True)

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

    def get_role(self, role_id, server_id):
        guild = self.client.get_guild(server_id)

        return SRole(guild.get_role(role_id))

    def get_user(self, user_id, server_id):
        guild = self.client.get_guild(server_id)

        return SUser(guild.get_member(user_id))

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

    async def send_file(self, data, fname, channel_id, server_id):
        server = client.get_guild(server_id)
        chan = server.get_channel(channel_id)

        file_desc = io.BytesIO(data)
        return await chan.send(file=discord.File(file_desc, filename=fname))

    async def send_message(self, text, channel_id, server_id):
        server = client.get_guild(server_id)
        chan = server.get_channel(channel_id)

        return await chan.send(content=text)

    async def send_embed(self, data, fname, channel_id, server_id):
        server = client.get_guild(server_id)
        chan = server.get_channel(channel_id)

        file_desc = io.BytesIO(data)
        return await chan.send(file=discord.File(file_desc, filename=fname))

    async def get_attachments(self, message_id, channel_id, server_id):
        chan = client.get_channel(channel_id)
        msg = await chan.fetch_message(message_id)

        att_list = []
        for attach in msg.attachments:
            att_list.append(attach.url)

        return att_list


class SServer(rpcobj.Server):
    def __init__(self, obj):
        self._raw = obj
        self.id = obj.id


class SRole(rpcobj.Role):
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
