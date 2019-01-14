import wand
import requests
import os
import string
import random
from wand.image import Image
from spanky.plugin import hook

def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def make_magik(url, storage_loc, send_file):
    img = requests.get(url).content

    wand_img = Image(blob=img)
    wand_img.transform(resize='800x800>')
    scale = 0

    wand_img.liquid_rescale(
            width=int(wand_img.width * 0.5),
            height=int(wand_img.height * 0.5),
            delta_x=int(0.5 * scale) if scale else 1, rigidity=0)

    wand_img.liquid_rescale(
            width=int(wand_img.width * 1.5),
            height=int(wand_img.height * 1.5),
            delta_x=scale if scale else 2, rigidity=0)

    os.system("mkdir -p " + storage_loc)
    fname = id_generator() + ".png"
    wand_img.save(filename=storage_loc + fname)

    send_file(open(storage_loc + fname, 'rb'))

    os.system("rm %s/%s" % (storage_loc, fname))

@hook.command()
def magik(event, send_file, storage_loc, get_emoji, text):
    if len(event.attachments) > 0:
        make_magik(event.attachments[0].url, storage_loc, send_file)
    elif len(event.embeds) > 0:
        make_magik(event.embeds[0].url, storage_loc, send_file)
    else:
        try:
            maybe_emoji = get_emoji(text.split()[0])
            if maybe_emoji:
                make_magik(maybe_emoji.url, storage_loc, send_file)
        except:
            url = "https://twemoji.maxcdn.com/72x72/{codepoint:x}.png".format(
                codepoint=ord(event.msg.clean_content.split()[1]))
            make_magik(url, storage_loc, send_file)