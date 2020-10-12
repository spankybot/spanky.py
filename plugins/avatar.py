import PIL
import io

from PIL import ImageFont, ImageDraw
from spanky.plugin import hook
from spanky.plugin.permissions import Permission
from spanky.utils.image import Image

BANNER_W = 960
BANNER_H = 540
DEFAULT_TEXT_SIZE = 80
TEXT_SPACE_H = 20

@hook.command(format="user")
def avatar(event, text, str_to_id):
    """<user or user-id> - Get someones avatar"""
    text = str_to_id(text)

    for user in event.server.get_users():
        if text == user.name:
            return user.avatar_url

        if text == user.id:
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
async def set_status(async_set_game_status, text):
    await async_set_game_status(text)

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


async def set_banner(server, pil_picture):
    """
    Set a banner from a PIL image
    """

    # Convert PIL to RAW
    raw_picture = io.BytesIO()
    pil_picture.save(raw_picture, format='PNG')
    raw_picture = raw_picture.getvalue()

    await server.set_banner(raw_picture)


async def update_banner(server, storage):
    """
    Refreshes the banner content
    """

    # Current image
    crt_banner = Image(url=storage["banner_url"])

    # Resize it
    resized = resize_to_fit(crt_banner.pil(), BANNER_W, BANNER_H)
    img_draw = ImageDraw.Draw(resized)

    # Find a good font size that fits the width
    font = None
    text_size = DEFAULT_TEXT_SIZE
    while True:
        font = ImageFont.truetype('plugin_data/fonts/OpenSansCondensed-Bold.ttf', text_size)
        text_width, text_height = img_draw.textsize(storage["banner_text"], font=font)

        # If text fits, break otherwise decrease size
        if text_width < BANNER_W and text_height < BANNER_H - TEXT_SPACE_H:
            break
        else:
            text_size -= 2

        if text_size <= 0:
            raise ValueError("Cannot fit text")

    img_draw.text((0, BANNER_H - text_height - TEXT_SPACE_H), storage["banner_text"], font=font, fill=(255,255,255,255))

    await set_banner(server, resized)

@hook.command(permissions=Permission.admin)
async def set_server_banner(event, server, storage):
    """
    Sets the server banner to a given URL
    """
    for img in event.image:
        storage["banner_url"] = img.url
        storage.sync()

        await update_banner(server, storage)
        return


@hook.command(permissions=Permission.admin)
async def set_banner_text(server, storage, text):
    """
    Sets the server banner text to a given content
    """
    storage["banner_text"] = text
    storage.sync()

    await update_banner(server, storage)