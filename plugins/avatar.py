import PIL
import io

from PIL import ImageFont, ImageDraw
from spanky.plugin import hook
from spanky.plugin.permissions import Permission
from spanky.utils.image import Image
from spanky.utils import discord_utils as dutils

BANNER_W = 960
BANNER_H = 540
DEFAULT_TEXT_SIZE = 80
TEXT_SPACE_W = BANNER_W // 10
TEXT_SPACE_H = 20


@hook.command(format="user")
def avatar(event, text, str_to_id):
    """<user or user-id> - Get someones avatar"""
    uid = str_to_id(text)

    for user in event.server.get_users():
        if text == user.name:
            return user.avatar_url

        if uid == user.id:
            return user.avatar_url

    return "Not found"


@hook.command(permissions=Permission.bot_owner)
async def set_avatar(event, async_set_avatar):
    """
    Set bot avatar
    """
    try:
        for img in event.image:
            img.fetch_url()
            await async_set_avatar(img._raw[0])
            return
    except:
        import traceback

        traceback.print_exc()


@hook.command(permissions=Permission.bot_owner)
async def set_status(async_set_game_status, reply, text):
    await async_set_game_status(text)
    return "Done"


@hook.command()
def e(event):
    """Expand an emoji"""
    return " ".join(event.url)


@hook.command()
def get_server_banner(server):
    """
    Return a link to the server banner
    """

    return server.banner_url


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
        (int(image.width / ratio), int(image.height / ratio)),
        resample=PIL.Image.ANTIALIAS,
    )

    # Paste the resized image in the center
    canvas.paste(
        image, (max_width // 2 - image.width // 2, max_height // 2 - image.height // 2)
    )

    return canvas


def fit_text_on_image(text):
    """
    Finds best fit for how the text fits in the banner.
    """
    img = Image()
    img.new_pil(mode="RGB", size=(BANNER_W, BANNER_H))
    img_draw = ImageDraw.Draw(img.pil())

    # Start from the default size and decrease font size.
    text_size = DEFAULT_TEXT_SIZE
    while True:
        font = ImageFont.truetype("plugin_data/fonts/plp.ttf", text_size)
        bbox = img_draw.textbbox(
            (0, 0), text, font=font, align="center", direction="ltr"
        )
        text_width, text_height = bbox[2], bbox[3]

        # If text fits, break otherwise decrease size
        if (
            text_width < BANNER_W - TEXT_SPACE_W
            and text_height < BANNER_H - TEXT_SPACE_H
        ):
            break
        else:
            text_size -= 2

        if text_size <= 0:
            raise ValueError("Cannot fit text")

    print(text_size)
    return font


def update_banner(server, storage):
    """
    Refreshes the banner content.
    """

    def process_one_frame(image):
        # Resize it
        resized = resize_to_fit(image, BANNER_W, BANNER_H)
        img_draw = ImageDraw.Draw(resized)
        img_draw.text(
            (BANNER_W // 2, BANNER_H // 2),
            banner_text,
            font=font,
            fill=(0, 0, 0, 255),
            anchor="mm",
            align="center",
        )

        return resized

    def send_file(to_send):
        print("setting " + to_send)

        import os

        print(os.stat(to_send).st_size)

        # Optimize gif using mogrify
        os.system(f"mogrify -layers 'optimize' -fuzz 7% {to_send}")
        print(os.stat(to_send).st_size)

        server.set_banner(open(to_send, "rb").read())

    def send_message(msg):
        print(msg)

    # Current image
    crt_banner = Image(url=storage["banner_url"])

    # Find a good font size that fits the width
    banner_text = storage["banner_text"].replace("`", "")
    font = fit_text_on_image(banner_text)

    # It could be a gif, so iterate through each frame
    crt_banner.proc_each_pil_frame(process_one_frame, send_file, send_message)


@hook.command(permissions=Permission.admin)
def set_server_banner(event, server, storage, reply):
    """
    Sets the server banner to a given URL
    """
    try:
        if not server.can_have_banner:
            reply("Server can't have banner")
            return

        for img in event.image:
            storage["banner_url"] = img.url
            storage.sync()

            update_banner(server, storage)
            return "Done"
        return "No image set."
    except Exception as e:
        import traceback

        traceback.print_exc()
        return "Error"


@hook.command(permissions=Permission.admin)
def set_banner_text(server, storage, text, reply):
    """
    Sets the server banner text to a given content
    """
    if not server.can_have_banner:
        reply("Server can't have banner")
        return

    storage["banner_text"] = text
    storage.sync()

    update_banner(server, storage)
