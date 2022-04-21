import os
from PIL import Image
from PIL import ImageFont
import json

base_dir = "resources/"


def get_filepath(relpath: str) -> str:
    return os.path.join(base_dir, relpath)


def get_path(category: str, name: str) -> str:
    return os.path.join(base_dir, category, name)


def load_json(name: str, category: str = "data") -> dict[str, any]:
    name = name.removesuffix(".json")
    with open(get_path(category, name + ".json"), "r") as f:
        return json.load(f)


def font(name: str = "default", size: int = 10) -> ImageFont.ImageFont:
    name = name.removesuffix(".ttf")
    try:
        return ImageFont.truetype(get_path("fonts", name + ".ttf"), size=size)
    except:
        print("Could not use chosen font. Using default.")
        return ImageFont.load_default()


def load_image(name: str, category: str = "data") -> Image.Image:
    return Image.open(get_path(category, name))


def load_file(name: str, category: str = "data") -> str:
    with open(get_path(category, name), "r") as f:
        return f.read()


def readlines(name: str, category: str = "data") -> list[str]:
    with open(get_path(category, name), "r") as f:
        return [line.strip() for line in f.readlines()]


# TODO: stuff for face.py
