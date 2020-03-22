from spanky.plugin import hook
import markovify
import os
import random

TEXTS_REL_PATH = "plugin_data/texts/"
RODDIT_ID = "287285563118190592"

MAX_OVERLAP_RATIO = 0.5
MAX_OVERLAP_TOTAL = 10

@hook.command(server_id=RODDIT_ID)
def shrug(send_message):
    send_message("¯\_(ツ)_/¯")

@hook.command(server_id=RODDIT_ID)
def dance(send_message, text):
    dance = [
            "└@(･◡･)@┐",
            "〈( ^.^)ノ",
            "ヽ(ﾟｰﾟ*ヽ)",
            "ヾ(´〇｀)ﾉ",
            "ヽ(´▽｀)ノ",]
    send_message(text + ": " + random.choice(dance))

@hook.command(server_id=RODDIT_ID)
def brutalistu(send_send_message):
    send_send_message("nu sunt bluntlee")

@hook.command(server_id=RODDIT_ID)
def bluntlee(send_message):
    send_message("nu sunt brutalistu")

@hook.command(server_id=RODDIT_ID)
def bitter(send_message):
    send_message("come play with me, Iazo")

@hook.command(server_id=RODDIT_ID)
def iazo(send_message):
    send_message(random.choice(["am treaba", "Ke"]))

@hook.command(server_id=RODDIT_ID)
def ayy(send_message):
    send_message("lmao")

@hook.command(server_id=RODDIT_ID)
def jupi(send_message):
    send_message("_rs _rs _rs _rs _rs _rs _rssss _rrrss erers Rs ERRES!!!")

@hook.command(server_id=RODDIT_ID)
def aplauze(send_message):
    send_message("CLAP CLAP CLAP CLAP CLAP")

@hook.command(server_id=RODDIT_ID)
def puti(send_message, text, nick):
    if text != "":
        send_message(text.split()[0] + ": Puţi!")
    else:
        send_message(nick + ": Puţi!")

@hook.command(server_id=RODDIT_ID)
def murmuz():
    with open(TEXTS_REL_PATH + "urmuz.txt", "r") as f:
        content = f.read()

        text_model = markovify.Text(content)
        try:
            return("murmuz: " + text_model.make_sentence(tries=1000,
                max_overlap_total=MAX_OVERLAP_TOTAL,
                max_overlap_ratio=MAX_OVERLAP_RATIO))
        except Exception as e:
            print(e)
            return "pula"

@hook.command(server_id=RODDIT_ID)
def mtutea():
    with open(TEXTS_REL_PATH + "Tutea.txt", "r", encoding ='ISO-8859-1') as f:
        content = f.read()

        text_model = markovify.Text(content)
        try:
            return("sluțea: " + text_model.make_sentence(tries=1000,
                max_overlap_total = MAX_OVERLAP_TOTAL,
                max_overlap_ratio=MAX_OVERLAP_RATIO))
        except Exception as e:
            print(e)
            return "a murit, mai dă-l in pulă"

@hook.command(server_id=RODDIT_ID)
def mpuric():
    with open(TEXTS_REL_PATH + "puric.txt", "r") as f:
        content = f.read()

        text_model = markovify.Text(content)
        try:
            return("pulic: " + text_model.make_sentence(tries=1000,
                max_overlap_total=MAX_OVERLAP_TOTAL,
                max_overlap_ratio=MAX_OVERLAP_RATIO))
        except Exception as e:
            print(e)
            return "pula"

@hook.command(server_id=RODDIT_ID)
def mcioran():
    with open(TEXTS_REL_PATH + "cioran.txt", "r") as f:
        content = f.read()

        text_model = markovify.Text(content)
        try:
            return("ciolan: " + text_model.make_short_sentence(max_chars = 140, tries=10000,
                max_overlap_total=MAX_OVERLAP_TOTAL,
                max_overlap_ratio=MAX_OVERLAP_RATIO))
        except Exception as e:
            return "pula"

@hook.command(server_id=RODDIT_ID)
def injur():
    with open(TEXTS_REL_PATH + "injuraturi.txt", "r") as f:
        content = f.read()

        text_model = markovify.Text(content)
        try:
            return("aihwh: " + text_model.make_short_sentence(max_chars = 140, tries=10000,
                max_overlap_total=MAX_OVERLAP_TOTAL,
                max_overlap_ratio=MAX_OVERLAP_RATIO))
        except Exception as e:
            return "pula"


@hook.command(server_id=RODDIT_ID)
def manea():
    with open(TEXTS_REL_PATH + "manele.txt", "r") as f:
        content = f.read()

        text_model = markovify.Text(content)
        try:
            return("lautar: " + text_model.make_short_sentence(max_chars = 300, tries=10000,
                max_overlap_total=MAX_OVERLAP_TOTAL,
                max_overlap_ratio=MAX_OVERLAP_RATIO))
        except Exception as e:
            return "pula"

@hook.command(server_id=RODDIT_ID)
def muie(send_message):
    send_message("ia muie!")

@hook.command(server_id=RODDIT_ID)
def cacat(send_message):
    send_message("ce cacat")

@hook.command(server_id=RODDIT_ID)
def cola():
    return "un cola pls!"
