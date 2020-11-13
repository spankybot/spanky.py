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
from gc import collect
from utils import time_utils

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

    def get_servers(self):
        """
        Get list of servers
        """
        servers = []
        for server in client.guilds:
            servers.append(SServer(server))

        return servers

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



class SServer(rpcobj.Server):
    def __init__(self, obj):
        self.id = obj.id
        self.name = obj.name


class SUser(rpcobj.User):
    def __init__(self, obj):
        self.id = obj.id
        self.name = obj.name
        self.display_name = obj.display_name


class SMessage(rpcobj.Message):
    def __init__(self, obj):
        self.content = obj.content
        self.id = obj.id
        self.author = SUser(obj.author)
        self.channel_id = obj.channel.id
        self.server_id = obj.guild.id

        self.clean_content = obj.clean_content


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
