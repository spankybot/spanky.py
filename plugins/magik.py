import wand
import requests
import os
import string
import random
import time
import subprocess
from wand.image import Image
from wand.image import Color
from spanky.plugin import hook
from oslo_concurrency import lockutils

def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

def get_image(url, raw=False):
    req = requests.get(url, stream=True)
    req.raise_for_status()

    size = 0
    start = time.time()

    content = bytes()
    for chunk in req.iter_content(1024):
        if time.time() - start > 20:
            raise()

        content += chunk
        size += len(chunk)

        if size > 1024 * 1024 * 20:
            return

    if raw:
        return content
    else:
        return Image(blob=content)

def send_img_reply(img, send_file, is_gif, storage_loc):
    if is_gif:
        ext = ".gif"
    else:
        ext = ".png"

    os.system("mkdir -p " + storage_loc)
    fname = id_generator() + ext
    img.save(filename=storage_loc + fname)

    send_file(open(storage_loc + fname, 'rb'))

    os.system("rm %s/%s" % (storage_loc, fname))

@lockutils.synchronized('not_thread_safe')
def make_df(url, storage_loc, send_file, send_message):
    try:
        wand_src = get_image(url)

        wand_img = Image()
        send_message("Working... %d frames" % len(wand_src.sequence))
        for frame in wand_src.sequence:
            frame.transform(resize='800x800>')

            frame.contrast_stretch(black_point=0.4, white_point=0.5)
            frame.modulate(saturation=800)
            frame.compression_quality = 2

            wand_img.sequence.append(frame)

        send_img_reply(wand_img, send_file, len(wand_src.sequence) > 1, storage_loc)
    except Exception as e:
        import traceback
        traceback.print_exc()
        send_message("Something went wrong")


@lockutils.synchronized('not_thread_safe')
def make_magik(url, storage_loc, send_file, send_message):
    try:
        wand_src = get_image(url)

        wand_img = Image()
        send_message("Working... %d frames" % len(wand_src.sequence))
        for frame in wand_src.sequence:
            frame.transform(resize='800x800>')
            scale = 0

            frame.liquid_rescale(
                width=int(frame.width * 0.5),
                height=int(frame.height * 0.5),
                delta_x=int(0.5 * scale) if scale else 1, rigidity=0)

            frame.liquid_rescale(
                width=int(frame.width * 1.5),
                height=int(frame.height * 1.5),
                delta_x=scale if scale else 2, rigidity=0)

            wand_img.sequence.append(frame)

        send_img_reply(wand_img, send_file, len(wand_src.sequence) > 1, storage_loc)
    except Exception as e:
        import traceback
        traceback.print_exc()
        send_message("Something went wrong")

@lockutils.synchronized('not_thread_safe')
def make_gmagik(url, storage_loc, send_file, send_message, ratio1=0.5, ratio2=1.5):
    try:
        wand_src = get_image(url)

        wand_img = Image()
        send_message("Working... ")
        frame = wand_src.sequence[0]

        frame.transform(resize='400x400>')
        frame.background = Color('black')
        frame.alpha_channel = 'remove'

        orig_width = frame.width
        orig_height = frame.height

        for i in range(16):
           frame.liquid_rescale(
                width=int(frame.width * ratio1),
                height=int(frame.height * ratio1),
                delta_x=1, rigidity=0)

           frame.liquid_rescale(
                width=int(frame.width * ratio2),
                height=int(frame.height * ratio2),
                delta_x=2, rigidity=0)

           frame.resize(orig_width, orig_height)

           wand_img.sequence.append(frame)

        send_img_reply(wand_img, send_file, True, storage_loc)
    except Exception as e:
        import traceback
        traceback.print_exc()
        send_message("Something went wrong")

@hook.command()
def df(event, send_file, storage_loc, text, send_message):
    for url in event.url:
        if url:
            make_df(url, storage_loc, send_file, send_message)
        else:
            return "Could not get image"

@hook.command()
def magik(event, send_file, storage_loc, text, send_message):
    for url in event.url:
        if url:
            make_magik(url, storage_loc, send_file, send_message)
        else:
            return "Could not get image"

@hook.command()
def gmagik(event, send_file, storage_loc, text, send_message):
    for url in event.url:
        if url:
            start = int(time.time())
            make_gmagik(url, storage_loc, send_file, send_message, 0.75, 1.25)
        else:
            return "Could not get image"

def make_gif(effect, url, storage_loc, send_file, send_message):
    try:
        wand_src = get_image(url)

        wand_src.transform(resize='400x400>')

        proc = subprocess.Popen(["gif", effect], stdin=subprocess.PIPE, stdout=subprocess.PIPE)

        out = proc.communicate(input=wand_src.make_blob("png"))[0]
        send_img_reply(Image(blob=out), send_file, True, storage_loc)
    except:
        import traceback
        traceback.print_exc()
        return "Ble"

@hook.command()
def ggif(event, send_file, storage_loc, text, send_message):
    if text == "":
        return "See: https://github.com/sgreben/yeetgif#usage"
    for url in event.url:
        if url:
            start = int(time.time())
            make_gif(text, url, storage_loc, send_file, send_message)
        else:
            return "Could not get image"

gif_effects = [
        "wobble",
        "roll",
        "pulse",
        "zoom",
        "shake",
        "woke",
        "fried",
        "hue",
        "tint",
        "crowd",
        "npc",
        "rain",
        "scan",
        "noise",
        "cat"
        ]

def init_funcs():
    def do_func(effect):
        def f(event, send_file, storage_loc, text, send_message):
            for url in event.url:
                if url:
                    make_gif(effect, url, storage_loc, send_file, send_message)
                else:
                    return "Could not get image"


        f.__name__ = effect

        return f

    for i in gif_effects:
        globals()[i] = hook.command()(do_func(i))

init_funcs()
