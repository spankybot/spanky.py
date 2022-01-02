import codecs
import json
import os
import random
import re

from spanky.plugin import hook
from spanky.utils import textgen
from spanky.plugin.permissions import Permission


def load_attacks():
    global larts, flirts, kills, slaps, north_korea, insults, strax, compliments, presents

    with codecs.open(os.path.join("plugin_data/larts.txt"), encoding="utf-8") as f:
        larts = [line.strip() for line in f.readlines() if not line.startswith("//")]

    with codecs.open(os.path.join("plugin_data/flirts.txt"), encoding="utf-8") as f:
        flirts = [line.strip() for line in f.readlines() if not line.startswith("//")]

    with codecs.open(os.path.join("plugin_data/insults.txt"), encoding="utf-8") as f:
        insults = [line.strip() for line in f.readlines() if not line.startswith("//")]

    with codecs.open(os.path.join("plugin_data/kills.json"), encoding="utf-8") as f:
        kills = json.load(f)

    with codecs.open(os.path.join("plugin_data/slaps.json"), encoding="utf-8") as f:
        slaps = json.load(f)

    with codecs.open(os.path.join("plugin_data/strax.json"), encoding="utf-8") as f:
        strax = json.load(f)

    with codecs.open(
        os.path.join("plugin_data/compliments.json"), encoding="utf-8"
    ) as f:
        compliments = json.load(f)

    with codecs.open(
        os.path.join("plugin_data/north_korea.txt"), encoding="utf-8"
    ) as f:
        north_korea = [
            line.strip() for line in f.readlines() if not line.startswith("//")
        ]

    with codecs.open(os.path.join("plugin_data/presents.json"), encoding="utf-8") as f:
        presents = json.load(f)


@hook.on_start()
def load():
    load_attacks()


@hook.command(permissions=Permission.bot_owner)
def reload_attacks():
    load_attacks()
    return "Reloaded."


@hook.command(format="user")
def lart(text):
    """<user> - LARTs <user>"""
    target = text.strip()
    phrase = random.choice(larts)

    # act out the message
    return phrase.format(user=target)


@hook.command(format="user")
def sexup(text):
    """<user> - flirts with <user>"""
    target = text.strip()

    return "{}, {}".format(target, random.choice(flirts))


@hook.command(name="kill")
def kill(text):
    """<user> - kills <user>"""
    target = text.strip()

    generator = textgen.TextGenerator(
        kills["templates"], kills["parts"], variables={"user": target}
    )

    # act out the message
    return generator.generate_string()


@hook.command()
def slap(text):
    """<user> -- Makes the bot slap <user>."""
    target = text.strip()

    variables = {"user": target}
    generator = textgen.TextGenerator(
        slaps["templates"], slaps["parts"], variables=variables
    )

    # act out the message
    return generator.generate_string()


@hook.command()
def compliment(text):
    """<user> -- Makes the bot compliment <user>."""
    target = text.strip()

    variables = {"user": target}
    generator = textgen.TextGenerator(
        compliments["templates"], compliments["parts"], variables=variables
    )

    # act out the message
    return generator.generate_string()


@hook.command()
def strax(text):
    """Strax quote."""

    if text:
        target = text.strip()
        variables = {"user": target}

        generator = textgen.TextGenerator(
            strax["target_template"], strax["parts"], variables=variables
        )
    else:
        generator = textgen.TextGenerator(strax["template"], strax["parts"])

    # Become Strax
    return generator.generate_string()


@hook.command()
def nk():
    """outputs a random North Korea propoganda slogan"""
    index = random.randint(0, len(north_korea) - 1)
    slogan = north_korea[index]
    return slogan


@hook.command()
def insult(text):
    """<user> - insults <user>"""
    target = text.strip()

    return "{}, {}".format(target, random.choice(insults))


@hook.command()
def gift(text):
    """<user> - gives gift to <user>"""
    target = text.strip()
    variables = {"user": target}

    generator = textgen.TextGenerator(
        presents["templates"], presents["parts"], variables=variables
    )
    return generator.generate_string()
