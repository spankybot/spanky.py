from SpankyWorker import hook
import markovify
import os
import random

TEXTS_REL_PATH = "plugin_data/texts/"
RODDIT_ID = "287285563118190592"

MAX_OVERLAP_RATIO = 0.5
MAX_OVERLAP_TOTAL = 10


@hook.command(server_id=RODDIT_ID)
def shrug(send_message):
    send_message(r"¯\_(ツ)_/¯")


@hook.command(server_id=RODDIT_ID)
def dance(send_message, text):
    dance = [
        "└@(･◡･)@┐",
        "〈( ^.^)ノ",
        "ヽ(ﾟｰﾟ*ヽ)",
        "ヾ(´〇｀)ﾉ",
        "ヽ(´▽｀)ノ", ]
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
    with open(TEXTS_REL_PATH + "Tutea.txt", "r", encoding='ISO-8859-1') as f:
        content = f.read()

        text_model = markovify.Text(content)
        try:
            return("sluțea: " + text_model.make_sentence(tries=1000,
                                                         max_overlap_total=MAX_OVERLAP_TOTAL,
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
        return("ciolan: " + text_model.make_short_sentence(max_chars=140, tries=10000,
                                                           max_overlap_total=MAX_OVERLAP_TOTAL,
                                                           max_overlap_ratio=MAX_OVERLAP_RATIO))


@hook.command(server_id=RODDIT_ID)
def injur():
    with open(TEXTS_REL_PATH + "injuraturi.txt", "r") as f:
        content = f.read()

        text_model = markovify.Text(content)
        return("aihwh: " + text_model.make_short_sentence(max_chars=140, tries=10000,
                                                          max_overlap_total=MAX_OVERLAP_TOTAL,
                                                          max_overlap_ratio=MAX_OVERLAP_RATIO))


@hook.command(server_id=RODDIT_ID)
def manea():
    with open(TEXTS_REL_PATH + "manele.txt", "r") as f:
        content = f.read()

        text_model = markovify.Text(content)

        return("lautar: " + text_model.make_short_sentence(max_chars=300, tries=10000,
                                                           max_overlap_total=MAX_OVERLAP_TOTAL,
                                                           max_overlap_ratio=MAX_OVERLAP_RATIO))


@hook.command(server_id=RODDIT_ID)
def muie(send_message):
    send_message("ia muie!")


@hook.command(server_id=RODDIT_ID)
def cacat(send_message):
    send_message("ce cacat")


@hook.command(server_id=RODDIT_ID)
def cola():
    return "un cola pls!"


@hook.command(server_id=RODDIT_ID)
def maslina(send_message, text):
    dance = [
        "ce zi minunata!",
        "ce faceti, prieteni?",
        "inca putin si se termina si ziua asta :D :D :D",
        "CUŢUUUUUUU!!!",
        "PISIIIIIII!!!"
    ]
    send_message(random.choice(dance))


@hook.command(server_id=RODDIT_ID)
def vasile(send_message, text):
    txt = [
        "vreau sa fut",
        "Imi place mult sa fut",
        "e singura manifestare care e umana",
        "miau trecut anii si de abia acum miam dat seama ca pula si pizda sunt cele mai importante organe mai tari deca t ministrul justitiei organele de interne ale SRI-ului organele prezidentiale pula si pizda si coaiele sunt cele mai tari lucruri",
        "vreau sa fut si eu sa ma simt bine",
        "negrii siau dat seama de mult americanii la fel au inalta stiinta au viagra ei au aduso si aici si face pula mare",
        "doctorii au descoperit multe panacee universale care face pule mari pule mari si coaie mari lucruri care vor sa si le revendice femeile acum pentru ca sunt batran si sunt la varsta senectutii",
        "intelepciunea mea nu depaseste organul genital eu am capul cap de pula",
        "nu imi trece sa am vreo manifestare vreo stiinta in mine daca mi se scoala pula",
        "vreau pizda vreau intre tate vreau in anus sa io bag si in multe alte alea la muie in gura sai bag",
        "vreau sami pun bile de aceea asteptatima sa imi pun bile 10 bile voi pune voi fute mai mult ca oricand acum la batranete"
    ]

    txt_en = [
        "I want to fuck"
        "I really like to fuck,"
        "it's the only deed that is human,"
        "my peak has passed and only now I realized that dick and pussy are the most important bodies better than the ministry of justice the bodies of internal affairs of the CIA the presidential boies dick and pussy and balls are the best things",
        "I want to fuck and I feel good,"
        "Blacks have long realized that Americans also have high science, they have viagra, they have brought it here and it's a big dick."
        "Doctors have discovered many universal panacea that makes big cocks big cocks and big balls things that women want to claim now because they are old and old in old age."
        "my wisdom does not exceed the genital organ I have the head of the head of the cock",
        "I don't care if I have any manifestation or science in me if my cock rises",
        "I want a pussy, I want between my tits, I want to put it in her anus and in many other things I put it in her mouth in her mouth",
        "I want to put balls on my own therefore wait to put balls 10 balls I will put I will fuck more than ever now that I'm old"
    ]

    if text == "en":
        send_message(random.choice(txt_en))
    else:
        send_message(random.choice(txt))
