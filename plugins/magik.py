import wand
import requests
import os
import string
import random
from wand.image import Image
from spanky.plugin import hook
from oslo_concurrency import lockutils

def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

def get_image(url):
    return Image(blob=requests.get(url).content)

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
def make_gmagik(url, storage_loc, send_file, send_message):
    try:
        wand_src = get_image(url)

        wand_img = Image()
        send_message("Working... ")
        frame = wand_src.sequence[0]

        #frame.transform(resize='800x800>')

        orig_width = frame.width
        orig_height = frame.height

        for i in range(8):
           frame.liquid_rescale(
                width=int(frame.width * 0.5),
                height=int(frame.height * 0.5),
                delta_x=1, rigidity=0)

           frame.liquid_rescale(
                width=int(frame.width * 1.5),
                height=int(frame.height * 1.5),
                delta_x=2, rigidity=0)

           frame.resize(orig_width, orig_height)

           wand_img.sequence.append(frame)

        send_img_reply(wand_img, send_file, True, storage_loc)
    except Exception as e:
        import traceback
        traceback.print_exc()
        send_message("Something went wrong")

def get_url(event, user_id_to_object, str_to_id, get_emoji, text):
    if len(event.attachments) > 0:
        return event.attachments[0].url
    elif len(event.embeds) > 0:
        return event.embeds[0].url
    elif user_id_to_object(str_to_id(text)) != None:
        return user_id_to_object(str_to_id(text)).avatar_url
    else:
        try:
            maybe_emoji = get_emoji(text.split()[0])
            if maybe_emoji:
                return maybe_emoji.url
        except:
            return "https://twemoji.maxcdn.com/72x72/{codepoint:x}.png".format(\
                    codepoint=ord(event.msg.clean_content.split()[1]))

@hook.command()
def magik(event, send_file, storage_loc, get_emoji, text, send_message, user_id_to_object, str_to_id):
    url = get_url(event, user_id_to_object, str_to_id, get_emoji, text)
    if url:
        print(url)
        make_magik(url, storage_loc, send_file, send_message)
    else:
        return "Could not get image"

@hook.command()
def gmagik(event, send_file, storage_loc, get_emoji, text, send_message, user_id_to_object, str_to_id):
    url = get_url(event, user_id_to_object, str_to_id, get_emoji, text)
    if url:
        print(url)
        make_gmagik(url, storage_loc, send_file, send_message)
    else:
        return "Could not get image"
