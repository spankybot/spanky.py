from spanky.plugin import hook
from datetime import datetime as dt
from dateutil import tz
from spanky.utils import discord_utils as dutils
import io
import discord
from spanky.utils.image import Image
import PIL
from PIL import ImageFont, ImageDraw
from spanky.plugin.permissions import Permission
import random

SERVER_IDS = [
    "648937029433950218", # Dev Server
    "287285563118190592" # r/ro
]

FUNNE_STUFF = [
    "buna dimineata, prieteni\n<oliv> 2020 colorizat",
    "mai bine fac integrale\n<vampy> 2020 colorizat", # 2019?
    "coaie am mancat, dar pula nu\n<bosche> 2020 colorizat", # 2019
    "mai bine fac un swipe cu cardul\nintre buci, ca ai POS\n<jungi> 2020 colorizat",
    "dupa voce poti sa-ti dai seama si\ncat de mult suge cineva pula\n<Aram> 2020 colorizat", # 2019
    "la Chaolena zodia e fox kids\nsi ascendentul e in cartoon network\n<junghi> 2020 colorizat",
    "tu esti la o pisica\ndistanta de menopauza\n<junghi> 2020 colorizat",
    "trebuie demarat un proiect national,\nceva cu finantare europeana.\n programul\n “un vibrator in fiecare noptiera”\n<zander> 2020 colorizat", # 2019
    "m-a luat la pula un mos beat\n care spunea ca el\ne iisus hristos\n<99problems> 2020 colorizat", # 2019
    "sa-ti numesti copilul\nAlex sau Andrei e ca si cum ai pune\n nume document new document\n<fantasy> 2020 colorizat",
    "mananci miros de pateu\npe umbra de paine\nsi insulti cantina, naine\n<pug> 2020 colorizat", # 2019
    "nu faci destui bani\ndaca nu ai dujmani\n<hater> 2020 colorizat",
    "mi-a mai inflorit patrunjelul, omg\n<oliv> 2020 colorizat",
    "baaa lasati cartile\nsi bagati pulanpizda baaa\n<Aram> 2020 colorizat",
    "FA ZDREANTO\nE GRATIS LA BISERICA\n<Pug> 2020 colorizat",
    "literalmente astia sunt\nmai gay decat mine\n<Febra> 2020 colorizat",
    "in spatele fiecarui audi\nse afla o femeie care\nnu a vrut sa se urce in logan\n<contra> 2020 colorizat", # 2018
    "vreau un tool care\nsa imi zica ca sunt prost\n<zak> 2020 colorizat"
]

TIMESTAMPS = [
    {"hour": 18, "minute": 0, "message": "Mai sunt 6 ore."},
    {"hour": 19, "minute": 0, "message": "Mai sunt 5 ore."},
    {"hour": 20, "minute": 0, "message": "Mai sunt 4 ore."},
    {"hour": 21, "minute": 0, "message": "Mai sunt 3 ore."},
    {"hour": 22, "minute": 0, "message": "Mai sunt 2 ore."},
    {"hour": 23, "minute": 0, "message": "Mai este o oră."},
    {"hour": 23, "minute": 15, "message": "Mai sunt 45 de minute."},
    {"hour": 23, "minute": 30, "message": "Mai sunt 30 de minute."},
    {"hour": 23, "minute": 45, "message": "Mai sunt 15 minute."},
    {"hour": 23, "minute": 50, "message": "Mai sunt 10 minute."},
    {"hour": 23, "minute": 51, "message": "Mai sunt 9 minute."},
    {"hour": 23, "minute": 52, "message": "Mai sunt 8 minute."},
    {"hour": 23, "minute": 53, "message": "Mai sunt 7 minute."},
    {"hour": 23, "minute": 54, "message": "Mai sunt 6 minute."},
    {"hour": 23, "minute": 55, "message": "Mai sunt 5 minute."},
    {"hour": 23, "minute": 56, "message": "Mai sunt 4 minute."},
    {"hour": 23, "minute": 57, "message": "Mai sunt 3 minute."},
    {"hour": 23, "minute": 58, "message": "Mai sunt 2 minute."},
    {"hour": 23, "minute": 59, "message": "Mai este un minut."},
    {"hour": 0, "minute": 0, "message": "La mulți ani, România!"},
]
ELEVATED_PERMS = [Permission.admin, Permission.bot_owner]
PERIOD = 1
PLUGIN_NAME = "plugins_custom_roddit_new_year.json"
TIMEZONE = tz.gettz("Europe/Bucharest")

URL = "https://cdn.kilonova.ro/m/xAV0YU/background_banner.png"

def get_message(time):
    hour, minute = time.hour, time.minute
    for t in TIMESTAMPS:
        if t["hour"] == hour and t["minute"] == minute:
            return t["message"]
    if  hour < 18 and hour >= 12:
        actual_time = (hour - 12) * 3 + minute // 20
        return FUNNE_STUFF[actual_time]
    return "Să rămână așa"
    
@hook.command(permissions=ELEVATED_PERMS, server_id=SERVER_IDS)
async def show_funne(async_send_file, event, async_send_message, text):
    if text == "":
        await async_send_message("Trimit tot ce consideri tu \"amuzant\"")
        for f in FUNNE_STUFF:
            await event.channel._raw.send(file=img_to_dfile(await get_banner(URL, f)))
        return
    try:
        nth = int(text)
        await event.channel._raw.send(file=img_to_dfile(await get_banner(URL, FUNNE_STUFF[nth])))
        return
    except Exception:
        await async_send_message("Nu-i valid input-ul")
        return
    await async_send_message("idk")

@hook.command(permissions=ELEVATED_PERMS, server_id=SERVER_IDS)
async def show_hours(event):
    for f in TIMESTAMPS:
        await event.channel._raw.send(file=img_to_dfile(await get_banner(URL, f["message"])))

@hook.periodic(PERIOD)
async def check(bot, send_message):
    time = dt.now(tz=TIMEZONE)
    for server in bot.backend.get_servers():
        if server.id not in SERVER_IDS:
            continue
        storage = bot.server_permissions[server.id].get_plugin_storage(PLUGIN_NAME)
        if "enabled" not in storage or not storage["enabled"]:
            continue
        if "current_message" not in storage:
            storage["current_message"] = ""
            storage.sync()
        msg = get_message(time)
        if msg == "Să rămână așa" or msg == storage["current_message"]:
            continue
        storage["current_message"] = msg
        storage.sync()
        img = await get_banner(URL, msg)
        dfile = img_to_dfile(img)
        
        if "do_banner" not in storage or not storage["do_banner"]:
            if server.id == "287285563118190592":
                ch = dutils.get_channel_by_id(server, "681141186156691468")
            else:
                ch = dutils.get_channel_by_id(server, "781942146093023283")
            if ch == None:
                print("Channel not found")
            await ch._raw.send(file=dfile)
        else:
            bio = io.BytesIO()
            img.save(bio, 'PNG')
            bio.seek(0)
            self.server.set_banner(bio)

@hook.command(permissions=ELEVATED_PERMS, server_id=SERVER_IDS)
def toggle_banner(storage):
    if "do_banner" not in storage or not storage["do_banner"]:
        storage["do_banner"] = True
        storage.sync()
        return "Am pornit actualizarea banner-ului"
    else:
        storage["do_banner"] = False
        storage.sync()
        return "Am oprit actualizarea banner-ului, voi trimite prin mesaj"

@hook.command(permissions=ELEVATED_PERMS, server_id=SERVER_IDS)
def enable_countdown(storage):
    storage["enabled"] = True
    storage["current_message"] = ""
    storage.sync()
    return "Enabled."

@hook.command(permissions=ELEVATED_PERMS, server_id=SERVER_IDS)
def disable_countdown(storage):
    storage["enabled"] = False
    storage["current_message"] = ""
    storage.sync()
    return "Disabled."

def img_to_dfile(img):
    bio = io.BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)
    return discord.File(bio, "banner.png")

# copied from avatar.py

BANNER_W = 960
BANNER_H = 540
DEFAULT_TEXT_SIZE = 80
TEXT_SPACE_W = BANNER_W // 8
TEXT_SPACE_H = 30
def resize_to_fit(image, max_width, max_height):
    """
    Resizes an image to best fit given constraints
    """
    # Create the canvas
    canvas = PIL.Image.new("RGBA", (max_width, max_height))

    # Calculate given and desired image w/h ratio
    given_img = image.width / image.height
    desired_img = max_width / max_height

    # If give image ratio is > then it's more wide than tall
    if given_img > desired_img:
        ratio = image.width / max_width
    else:
        ratio = image.height / max_height

    # Resize it
    image = image.resize(
                (
                    int(image.width / ratio),
                    int(image.height / ratio)
                ),
            resample=PIL.Image.ANTIALIAS)

    # Paste the resized image in the center
    canvas.paste(image,
        (
            max_width // 2 - image.width // 2,
            max_height // 2 - image.height // 2)
        )

    return canvas


async def get_banner(banner_url, banner_text):
    """
    Refreshes the banner content
    """

    # Current image
    crt_banner = Image(banner_url)

    # Resize it
    resized = resize_to_fit(crt_banner.pil(), BANNER_W, BANNER_H)
    img_draw = ImageDraw.Draw(resized)

    # Find a good font size that fits the width
    font = None
    text_size = DEFAULT_TEXT_SIZE
    while True:
        font = ImageFont.truetype('plugin_data/fonts/plp.ttf', text_size)
        bbox = img_draw.textbbox((0,0), banner_text, font=font, align="center", direction="ltr")
        text_width, text_height = bbox[2], bbox[3]
        # If text fits, break otherwise decrease size
        if text_width < BANNER_W - TEXT_SPACE_W and text_height < BANNER_H // 2 - TEXT_SPACE_H:
            break
        else:
            text_size -= 2

        if text_size <= 0:
            raise ValueError("Cannot fit text")

    img_draw.text((BANNER_W // 2, 260),
            banner_text, font=font, fill=(255,255,255,255), anchor="ma", align="center", direction="ltr")

    return resized
