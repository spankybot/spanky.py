import PIL
import PIL.Image
import PIL.ImageFont
import PIL.ImageOps
import PIL.ImageDraw
from spanky.plugin import hook
from spanky.plugin.permissions import Permission
from spanky.plugin.event import EventType
import requests
import os
import re
import random
import string
PIXEL_ON = 0  # PIL color to use for "on"
PIXEL_OFF = 255  # PIL color to use for "off"


@hook.command()
def text_image(string, font_path=None, font_size=30, font_color=None, font_bg=None):
    grayscale = 'RGBA'
    lines = string
    font_color = font_color or "white"
    large_font = font_size or 30  #
    font_path = font_path or 'plugin_data/fonts/sofia.ttf'
    font_bg = font_bg or (255, 255, 255, 0)
    try:
        font = PIL.ImageFont.truetype(font_path, size=large_font)
    except IOError:
        font = PIL.ImageFont.load_default()
        print('Could not use chosen font. Using default.')

    def pt2px(pt): return int(round(pt * 46.0 / 45))
    max_width_line = max(lines, key=lambda s: font.getsize(s)[0])
    test_string = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    max_height = pt2px(font.getsize(test_string)[1])
    max_width = pt2px(font.getsize(max_width_line)[0])
    height = max_height * len(lines) + 40
    width = int(round(max_width + 120))
    image = PIL.Image.new(grayscale, (width, height), color=font_bg)
    draw = PIL.ImageDraw.Draw(image)
    vertical_position = 25
    horizontal_position = 25
    line_spacing = int(round(max_height * 0.9))  # reduced spacing seems better
    for line in lines:
        draw.text((horizontal_position, vertical_position),
                  line, fill=font_color, font=font, stroke_width=1, stroke_fill="black")
        vertical_position += line_spacing

    return image


@hook.command()
def txt2img(text, event, send_file, reply):
    """
    Generate a image using sent text
    "<option> - available input for custom fonts:
    .image <font name>-<size>-<text color>-<bg color>
    VALID_FONTS=
    'sofia',
    'ostirch',
    'diso',
    'learning',
    'hotel',
    'plp',
    'default'
    'symbols'
    Example usage of this command :
    .text2img sofia-30-red-yellow the quick brown fox jumps over the lazy dog
    """
    VALID_FONTS = ['sofia', 'ostirch', 'diso', 'learning',
                   'hotel', 'symbols', 'plp', 'diso', 'default']
    strd = str.splitlines(text)
    parameters = strd[0].split(maxsplit=1)
    param = parameters[0].split('-')
    font = 'symbols'
    if(len(param) > 0 and len(strd) > 0):
        if param[0] in VALID_FONTS:
            strd[0] = strd[0].split(' ', 1)[1]
            font = param[0]
    font_size = 30
    font_color = "white"
    if(len(param) > 1 and int(param[1]) > 1 and int(param[1]) < 200):
        font_size = param[1]
    if(len(param) > 2):
        font_color = param[2]
    font_bg = None
    try:
        if(len(param) > 3):
            font_bg = param[3]
    except Error:
        print("bg color not found")
    font += '.ttf'
    font = 'plugin_data/fonts/' + font
    image = text_image(strd, font, int(font_size), font_color, font_bg)
    image.save('txt2img.png')
    send_file('txt2img.png')
