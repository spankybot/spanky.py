import operator
import random
import discord
from collections import defaultdict
from time import time

from sqlalchemy import Table, Column, String, Integer, PrimaryKeyConstraint, desc, Boolean
from sqlalchemy.sql import select

from spanky import hook
from spanky.event import EventType
from spanky import database

duck_tail = "・゜゜・。。・゜゜"
duck = ["\_o< ", "\_O< ", "\_0< ", "\_\u00f6< ", "\_\u00f8< ", "\_\u00f3< "]
duck_noise = ["QUACK!", "FLAP FLAP!", "quack!"]

table = Table(
    'duck_hunt',
    database.metadata,
    Column('network', String),
    Column('name', String),
    Column('shot', Integer),
    Column('befriend', Integer),
    Column('chan', String),
    PrimaryKeyConstraint('name', 'chan', 'network')
)

status_table = Table(
    'duck_status',
    database.metadata,
    Column('network', String),
    Column('chan', String),
    Column('active', Boolean, default=False),
    Column('duck_kick', Boolean, default=False),
    PrimaryKeyConstraint('network', 'chan')
)

"""
game_status structure
{
    'network':{
        '#chan1':{
            'duck_status':0|1|2,
            'next_duck_time':'integer',
            'game_on':0|1,
            'no_duck_kick': 0|1,
            'duck_time': 'float',
            'shoot_time': 'float',
            'messages': integer,
            'masks' : list
        }
    }
}
"""

MSG_DELAY = 10
MASK_REQ = 3
scripters = defaultdict(int)
game_status = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

# TODO:
game_status["roddit"]["bot-playground"]["game_on"] = 1


e_duck = "mac mac"
e_turkey = "gobble gobble"
e_rooster = "cucurigu"

@hook.periodic(5 * 60, initial_interval=10 * 60)
def save_status(db):
    for network in game_status:
        for chan, status in game_status[network].items():
            active = bool(status['game_on'])
            duck_kick = bool(status['no_duck_kick'])
            res = db.execute(status_table.update().where(status_table.c.network == network).where(
                status_table.c.chan == chan).values(
                active=active, duck_kick=duck_kick
            ))
            if not res.rowcount:
                try:
                    db.execute(status_table.insert().values(network=network, chan=chan, active=active, duck_kick=duck_kick))
                except IntegrityError:
                    db.session.rollback()

            db.commit()


@hook.event([EventType.message, EventType.action], singlethread=True)
def incrementMsgCounter(event, conn):
    """Increment the number of messages said in an active game channel. Also keep track of the unique masks that are speaking."""
    global game_status
    if game_status[conn.name][event.chan]['game_on'] == 1 and game_status[conn.name][event.chan]['duck_status'] == 0:
        game_status[conn.name][event.chan]['messages'] += 1
        #if event.host not in game_status[conn.name][event.chan]['masks']:
        #    game_status[conn.name][event.chan]['masks'].append(event.host)


@hook.command("starthunt", autohelp=False, permissions=["chanop", "op", "botcontrol"])
def start_hunt(chan, message, conn):
    """- This command starts a duckhunt in your channel, to stop the hunt use .stophunt"""
    global game_status
    check = game_status[conn.name][chan]['game_on']
    if check:
        return "there is already a game running in {}.".format(chan)
    else:
        game_status[conn.name][chan]['game_on'] = 1
    set_ducktime(chan, conn.name)
    message(
        "Ducks have been spotted nearby. See how many you can shoot or save. use .bang to shoot or .befriend to save them. NOTE: Ducks now appear as a function of time and channel activity.",
        chan)


def set_ducktime(chan, conn):
    global game_status
    game_status[conn][chan]['next_duck_time'] = random.randint(int(time()) + 480, int(time()) + 3600)
    #game_status[conn][chan]['next_duck_time'] = int(time())
    game_status[conn][chan]['flyaway'] = game_status[conn][chan]['next_duck_time'] + 600
    game_status[conn][chan]['duck_status'] = 0
    # let's also reset the number of messages said and the list of masks that have spoken.
    game_status[conn][chan]['messages'] = 0
    game_status[conn][chan]['masks'] = []
    return


@hook.command("stophunt", autohelp=False, permissions=["chanop", "op", "botcontrol"])
def stop_hunt(chan, conn):
    """- This command stops the duck hunt in your channel. Scores will be preserved"""
    global game_status
    if game_status[conn.name][chan]['game_on']:
        game_status[conn.name][chan]['game_on'] = 0
        return "the game has been stopped."
    else:
        return "There is no game running in {}.".format(chan)


def generate_duck(server):
    """Try and randomize the duck message so people can't highlight on it/script against it."""
    #rt = random.randint(1, len(duck_tail) - 1)
    #dtail = duck_tail[:rt] + u' \u200b ' + duck_tail[rt:]
    #dbody = random.choice(duck)
    #rb = random.randint(1, len(dbody) - 1)
    #dbody = dbody[:rb] + u'\u200b' + dbody[rb:]
    #dnoise = random.choice(duck_noise)
    #rn = random.randint(1, len(dnoise) - 1)
    #dnoise = dnoise[:rn] + u'\u200b' + dnoise[rn:]
    #return dtail, dbody, dnoise

    emoji_ch = random.choice(["🐦", "🐔", "🦃"])

    message = ""
    for i in range(random.randint(4, 9)):
        message += " " + emoji_ch

    return message + " " + random.choice(duck_noise)


@hook.periodic(1)
def deploy_duck(bot, server):
    global game_status
    for network in game_status:
        if network not in bot.connections:
            continue
        conn = bot.connections[network]
        if not conn.ready:
            continue
        for chan in game_status[network]:
            active = game_status[network][chan]['game_on']
            duck_status = game_status[network][chan]['duck_status']
            next_duck = game_status[network][chan]['next_duck_time']
            chan_messages = game_status[network][chan]['messages']
            chan_masks = game_status[network][chan]['masks']
            if active == 1 and duck_status == 0 and next_duck <= time() and chan_messages >= MSG_DELAY:
                # deploy a duck to channel
                game_status[network][chan]['duck_status'] = 1
                game_status[network][chan]['duck_time'] = time()
                #dtail, dbody, dnoise = generate_duck(bot)
                #conn.message(chan, "{}{}{}".format(dtail, dbody, dnoise))
                conn.message(chan, generate_duck(bot.discord_client))
            continue
        continue


def hit_or_miss(deploy, shoot):
    """This function calculates if the befriend or bang will be successful."""
    if shoot - deploy < 1:
        return .05
    elif 1 <= shoot - deploy <= 7:
        out = random.uniform(.60, .75)
        return out
    else:
        return 1


def dbadd_entry(nick, chan, db, conn, shoot, friend):
    """Takes care of adding a new row to the database."""
    query = table.insert().values(
        network=conn.name,
        chan=chan.lower(),
        name=nick.lower(),
        shot=shoot,
        befriend=friend)
    db.execute(query)
    db.commit()


def dbupdate(nick, chan, db, conn, shoot, friend):
    """update a db row"""
    if shoot and not friend:
        query = table.update() \
            .where(table.c.network == conn.name) \
            .where(table.c.chan == chan.lower()) \
            .where(table.c.name == nick.lower()) \
            .values(shot=shoot)
        db.execute(query)
        db.commit()
    elif friend and not shoot:
        query = table.update() \
            .where(table.c.network == conn.name) \
            .where(table.c.chan == chan.lower()) \
            .where(table.c.name == nick.lower()) \
            .values(befriend=friend)
        db.execute(query)
        db.commit()
    elif friend and shoot:
        query = table.update() \
            .where(table.c.network == conn.name) \
            .where(table.c.chan == chan.lower()) \
            .where(table.c.name == nick.lower()) \
            .values(befriend=friend) \
            .values(shot=shoot)
        db.execute(query)
        db.commit()


def update_score(nick, chan, db, conn, shoot=0, friend=0):
    score = db.execute(select([table.c.shot, table.c.befriend])
                       .where(table.c.network == conn.name)
                       .where(table.c.chan == chan.lower())
                       .where(table.c.name == nick.lower())).fetchone()
    if score:
        dbupdate(nick, chan, db, conn, score[0] + shoot, score[1] + friend)
        return {'shoot': score[0] + shoot, 'friend': score[1] + friend}
    else:
        dbadd_entry(nick, chan, db, conn, shoot, friend)
        return {'shoot': shoot, 'friend': friend}


def attack(nick, chan, message, db, conn, notice, server, attack):
    global game_status, scripters

    network = conn.name
    status = game_status[network][chan]

    mue = str(discord.utils.get(server.emojis, name='viomuie'))

    out = ""
    if attack == "shoot":
        miss = [
            "WHOOSH! You missed the duck completely!", "Your gun jammed!",
            "Better luck next time.",
            "WTF?! Who are you, Kim Jong Un firing missiles? You missed."
        ]
        no_duck = "There is no duck! What are you shooting at? " + mue
        msg = "{} you shot a duck in {:.3f} seconds! You have killed {} in {}."
        scripter_msg = "You pulled the trigger in {:.3f} seconds, that's mighty fast. Are you sure you aren't a script? Take a 2 hour cool down."
        attack_type = "shoot"
    else:
        miss = [
            "The duck didn't want to be friends, maybe next time.",
            "Well this is awkward, the duck needs to think about it.",
            "The duck said no, maybe bribe it with some pizza? Ducks love pizza don't they?",
            "Who knew ducks could be so picky?",
            "Duck said %s" % mue
        ]
        no_duck = "You tried befriending a non-existent duck. That's freaking creepy."
        msg = "{} you befriended a duck in {:.3f} seconds! You have made friends with {} in {}."
        scripter_msg = "You tried friending that duck in {:.3f} seconds, that's mighty fast. Are you sure you aren't a script? Take a 2 hour cool down."
        attack_type = "friend"

    if not status['game_on']:
        return "There is no hunt right now. Use .starthunt to start a game."
    elif status['duck_status'] != 1:
        if status['no_duck_kick'] == 1:
            conn.cmd("KICK", chan, nick, no_duck)
            return

        return no_duck
    else:
        status['shoot_time'] = time()
        deploy = status['duck_time']
        shoot = status['shoot_time']
        if nick.lower() in scripters:
            if scripters[nick.lower()] > shoot:
                notice(
                    "You are in a cool down period, you can try again in {:.3f} seconds.".format(
                        scripters[nick.lower()] - shoot
                    )
                )
                return

        chance = hit_or_miss(deploy, shoot)
        if not random.random() <= chance and chance > .05:
            out = random.choice(miss) + " You can try again in 7 seconds."
            scripters[nick.lower()] = shoot + 7
            return out

        if chance == .05:
            out += scripter_msg.format(shoot - deploy)
            scripters[nick.lower()] = shoot + 7200
            if not random.random() <= chance:
                return random.choice(miss) + " " + out
            else:
                message(out)

        status['duck_status'] = 2
        try:
            args = {
                attack_type: 1
            }

            score = update_score(nick, chan, db, conn, **args)[attack_type]
        except Exception:
            status['duck_status'] = 1
            raise

        message(msg.format(nick, shoot - deploy, pluralize(score, "duck"), chan))
        set_ducktime(chan, conn.name)


@hook.command("bang", autohelp=False)
def bang(nick, chan, message, db, conn, notice, server):
    """- when there is a duck on the loose use this command to shoot it."""
    return attack(nick, chan, message, db, conn, notice, server, "shoot")


@hook.command("befriend", autohelp=False)
def befriend(nick, chan, message, db, conn, notice, server):
    """- when there is a duck on the loose use this command to befriend it before someone else shoots it."""
    return attack(nick, chan, message, db, conn, notice, server, "befriend")


def smart_truncate(content, length=320, suffix='...'):
    if len(content) <= length:
        return content
    else:
        return content[:length].rsplit(' • ', 1)[0] + suffix


@hook.command("friends", autohelp=False)
def friends(text, chan, conn, db):
    """[{global|average}] - Prints a list of the top duck friends in the channel, if 'global' is specified all channels in the database are included."""
    friends = defaultdict(int)
    chancount = defaultdict(int)
    if text.lower() == 'global' or text.lower() == 'average':
        out = "Duck friend scores across the network: "
        scores = db.execute(select([table.c.name, table.c.befriend]) \
                            .where(table.c.network == conn.name) \
                            .order_by(desc(table.c.befriend)))
        if scores:
            for row in scores:
                if row[1] == 0:
                    continue
                chancount[row[0]] += 1
                friends[row[0]] += row[1]
            if text.lower() == 'average':
                for k, v in friends.items():
                    friends[k] = int(v / chancount[k])
        else:
            return "it appears no on has friended any ducks yet."
    else:
        out = "Duck friend scores in {}: ".format(chan)
        scores = db.execute(select([table.c.name, table.c.befriend]) \
                            .where(table.c.network == conn.name) \
                            .where(table.c.chan == chan.lower()) \
                            .order_by(desc(table.c.befriend)))
        if scores:
            for row in scores:
                if row[1] == 0:
                    continue
                friends[row[0]] += row[1]
        else:
            return "it appears no on has friended any ducks yet."

    topfriends = sorted(friends.items(), key=operator.itemgetter(1), reverse=True)
    out += ', '.join(["{}: {}".format('\x02' + k[:1] + u'\u200b' + k[1:] + '\x02', str(v)) for k, v in topfriends])
    out = smart_truncate(out)
    return out


@hook.command("killers", autohelp=False)
def killers(text, chan, conn, db):
    """[{global|average}] - Prints a list of the top duck killers in the channel, if 'global' is specified all channels in the database are included."""
    killers = defaultdict(int)
    chancount = defaultdict(int)
    if text.lower() == 'global' or text.lower() == 'average':
        out = "Duck killer scores across the network: "
        scores = db.execute(select([table.c.name, table.c.shot]) \
                            .where(table.c.network == conn.name) \
                            .order_by(desc(table.c.shot)))
        if scores:
            for row in scores:
                if row[1] == 0:
                    continue
                chancount[row[0]] += 1
                killers[row[0]] += row[1]
            if text.lower() == 'average':
                for k, v in killers.items():
                    killers[k] = int(v / chancount[k])
        else:
            return "it appears no on has killed any ducks yet."
    else:
        out = "Duck killer scores in {}: ".format(chan)
        scores = db.execute(select([table.c.name, table.c.shot]) \
                            .where(table.c.network == conn.name) \
                            .where(table.c.chan == chan.lower()) \
                            .order_by(desc(table.c.shot)))
        if scores:
            for row in scores:
                if row[1] == 0:
                    continue
                killers[row[0]] += row[1]
        else:
            return "it appears no on has killed any ducks yet."

    topkillers = sorted(killers.items(), key=operator.itemgetter(1), reverse=True)
    out += ', '.join(["{}: {}".format('\x02' + k[:1] + u'\u200b' + k[1:] + '\x02', str(v)) for k, v in topkillers])
    out = smart_truncate(out)
    return out


@hook.command("duckforgive", permissions=["op", "ignore"])
def duckforgive(text):
    """<nick> - Allows people to be removed from the mandatory cooldown period."""
    global scripters
    if text.lower() in scripters and scripters[text.lower()] > time():
        scripters[text.lower()] = 0
        return "{} has been removed from the mandatory cooldown period.".format(text)
    else:
        return "I couldn't find anyone banned from the hunt by that nick"


@hook.command("duckmerge", permissions=["botcontrol"])
def duck_merge(text, conn, db, message):
    """<user1> <user2> - Moves the duck scores from one nick to another nick. Accepts two nicks as input the first will have their duck scores removed the second will have the first score added. Warning this cannot be undone."""
    oldnick, newnick = text.lower().split()
    if not oldnick or not newnick:
        return "Please specify two nicks for this command."
    oldnickscore = db.execute(select([table.c.name, table.c.chan, table.c.shot, table.c.befriend])
                              .where(table.c.network == conn.name)
                              .where(table.c.name == oldnick)).fetchall()
    newnickscore = db.execute(select([table.c.name, table.c.chan, table.c.shot, table.c.befriend])
                              .where(table.c.network == conn.name)
                              .where(table.c.name == newnick)).fetchall()
    duckmerge = defaultdict(lambda: defaultdict(int))
    duckmerge["TKILLS"] = 0
    duckmerge["TFRIENDS"] = 0
    channelkey = {"update": [], "insert": []}
    if oldnickscore:
        if newnickscore:
            for row in newnickscore:
                duckmerge[row["chan"]]["shot"] = row["shot"]
                duckmerge[row["chan"]]["befriend"] = row["befriend"]
            for row in oldnickscore:
                if row["chan"] in duckmerge:
                    duckmerge[row["chan"]]["shot"] = duckmerge[row["chan"]]["shot"] + row["shot"]
                    duckmerge[row["chan"]]["befriend"] = duckmerge[row["chan"]]["befriend"] + row["befriend"]
                    channelkey["update"].append(row["chan"])
                    duckmerge["TKILLS"] = duckmerge["TKILLS"] + row["shot"]
                    duckmerge["TFRIENDS"] = duckmerge["TFRIENDS"] + row["befriend"]
                else:
                    duckmerge[row["chan"]]["shot"] = row["shot"]
                    duckmerge[row["chan"]]["befriend"] = row["befriend"]
                    channelkey["insert"].append(row["chan"])
                    duckmerge["TKILLS"] = duckmerge["TKILLS"] + row["shot"]
                    duckmerge["TFRIENDS"] = duckmerge["TFRIENDS"] + row["befriend"]
        else:
            for row in oldnickscore:
                duckmerge[row["chan"]]["shot"] = row["shot"]
                duckmerge[row["chan"]]["befriend"] = row["befriend"]
                channelkey["insert"].append(row["chan"])
                # TODO: Call dbupdate() and db_add_entry for the items in duckmerge
        for channel in channelkey["insert"]:
            dbadd_entry(newnick, channel, db, conn, duckmerge[channel]["shot"], duckmerge[channel]["befriend"])
        for channel in channelkey["update"]:
            dbupdate(newnick, channel, db, conn, duckmerge[channel]["shot"], duckmerge[channel]["befriend"])
        query = table.delete() \
            .where(table.c.network == conn.name) \
            .where(table.c.name == oldnick)
        db.execute(query)
        db.commit()
        message("Migrated {} duck kills and {} duck friends from {} to {}".format(duckmerge["TKILLS"],
                                                                                  duckmerge["TFRIENDS"], oldnick,
                                                                                  newnick))
    else:
        return "There are no duck scores to migrate from {}".format(oldnick)


@hook.command("ducks", autohelp=False)
def ducks_user(text, nick, chan, conn, db, message):
    """<nick> - Prints a users duck stats. If no nick is input it will check the calling username."""
    name = nick.lower()
    if text:
        name = text.split()[0].lower()
    ducks = defaultdict(int)
    scores = db.execute(select([table.c.name, table.c.chan, table.c.shot, table.c.befriend])
                        .where(table.c.network == conn.name)
                        .where(table.c.name == name)).fetchall()
    if text:
        name = text.split()[0]
    else:
        name = nick
    if scores:
        has_hunted_in_chan = False
        for row in scores:
            if row["chan"].lower() == chan.lower():
                has_hunted_in_chan = True
                ducks["chankilled"] += row["shot"]
                ducks["chanfriends"] += row["befriend"]
            ducks["killed"] += row["shot"]
            ducks["friend"] += row["befriend"]
            ducks["chans"] += 1
        # Check if the user has only participated in the hunt in this channel
        if ducks["chans"] == 1 and has_hunted_in_chan:
            message("{} has killed {} and befriended {} ducks in {}.".format(name, ducks["chankilled"],
                                                                             ducks["chanfriends"], chan))
            return
        kill_average = int(ducks["killed"] / ducks["chans"])
        friend_average = int(ducks["friend"] / ducks["chans"])
        message(
            "\x02{}'s\x02 duck stats: \x02{}\x02 killed and \x02{}\x02 befriended in {}. Across {} channels: \x02{}\x02 killed and \x02{}\x02 befriended. Averaging \x02{}\x02 kills and \x02{}\x02 friends per channel.".format(
                name, ducks["chankilled"], ducks["chanfriends"], chan, ducks["chans"], ducks["killed"], ducks["friend"],
                kill_average, friend_average))
    else:
        return "It appears {} has not participated in the duck hunt.".format(name)


@hook.command("duckstats", autohelp=False)
def duck_stats(chan, conn, db, message):
    """- Prints duck statistics for the entire channel and totals for the network."""
    ducks = defaultdict(int)
    scores = db.execute(select([table.c.name, table.c.chan, table.c.shot, table.c.befriend])
                        .where(table.c.network == conn.name)).fetchall()
    if scores:
        ducks["friendchan"] = defaultdict(int)
        ducks["killchan"] = defaultdict(int)
        for row in scores:
            ducks["friendchan"][row["chan"]] += row["befriend"]
            ducks["killchan"][row["chan"]] += row["shot"]
            # ducks["chans"] += 1
            if row["chan"].lower() == chan.lower():
                ducks["chankilled"] += row["shot"]
                ducks["chanfriends"] += row["befriend"]
            ducks["killed"] += row["shot"]
            ducks["friend"] += row["befriend"]
        ducks["chans"] = int((len(ducks["friendchan"]) + len(ducks["killchan"])) / 2)
        killerchan, killscore = sorted(ducks["killchan"].items(), key=operator.itemgetter(1), reverse=True)[0]
        friendchan, friendscore = sorted(ducks["friendchan"].items(), key=operator.itemgetter(1), reverse=True)[0]
        message(
            "\x02Duck Stats:\x02 {} killed and {} befriended in \x02{}\x02. Across {} channels \x02{}\x02 ducks have been killed and \x02{}\x02 befriended. \x02Top Channels:\x02 \x02{}\x02 with {} kills and \x02{}\x02 with {} friends".format(
                ducks["chankilled"], ducks["chanfriends"], chan, ducks["chans"], ducks["killed"], ducks["friend"],
                killerchan, killscore, friendchan, friendscore))
    else:
        return "It looks like there has been no duck activity on this channel or network."
