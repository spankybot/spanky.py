import subprocess
from spanky.plugin import hook
from oslo_concurrency import lockutils
from wand.image import Image as wand_img


@lockutils.synchronized('not_thread_safe')
def make_df(frame):
    frame.transform(resize='800x800>')

    frame.contrast_stretch(black_point=0.4, white_point=0.5)
    frame.modulate(saturation=800)
    frame.compression_quality = 2

    return frame


@hook.command()
def df(event, send_file, send_message):
    """
    Deepfry image
    """
    for img in event.image:
        img.proc_each_wand_frame(make_df, send_file, send_message)


@lockutils.synchronized('not_thread_safe')
def make_flip(frame):
    frame.flip()
    return frame


@hook.command()
def flip(event, send_file, send_message):
    """
    Flip image horizontally
    """
    for img in event.image:
        img.proc_each_wand_frame(make_flip, send_file, send_message)


@lockutils.synchronized('not_thread_safe')
def make_resize(frame, width, height):
    frame.resize(width, height)
    return frame


@hook.command(params="int:width int:height")
def resize(event, send_file, send_message, cmd_args):
    """
    Resize image
    """
    for img in event.image:
        img.proc_each_wand_frame(
            make_resize, send_file, send_message, cmd_args)


@lockutils.synchronized('not_thread_safe')
def make_flop(frame):
    frame.flop()
    return frame


@hook.command()
def flop(event, send_file, send_message):
    """
    Flip image vertically
    """
    for img in event.image:
        img.proc_each_wand_frame(make_flop, send_file, send_message)


@lockutils.synchronized('not_thread_safe')
def make_implode(frame, amount):
    print(amount)
    frame.implode(amount)
    return frame


@hook.command(params="float:amount=0.5")
def implode(event, send_file, send_message, cmd_args):
    """
    Implode image
    """
    for img in event.image:
        img.proc_each_wand_frame(
            make_implode, send_file, send_message, cmd_args)


def make_negate(frame):
    frame.negate()
    return frame


@hook.command()
def negate(event, send_file, send_message):
    """
    Invert colors
    """
    for img in event.image:
        img.proc_each_wand_frame(make_negate, send_file, send_message)


def make_imgtext(frame, text):
    frame.transform(resize='400x400>')

    proc = subprocess.Popen(["gif", "text", text], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE)

    out = proc.communicate(wand_img(frame).make_blob("png"))[0]

    result = wand_img(blob=out)
    return result


@hook.command(params="string:text")
def img_text(event, send_file, send_message, cmd_args):
    """
    Add text to image
    """
    for img in event.image:
        img.proc_each_wand_frame(
            make_imgtext, send_file, send_message, cmd_args)


def make_gif_app_caller(frame, effect):
    frame.transform(resize='400x400>')

    proc = subprocess.Popen(["gif", effect], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE)

    out = proc.communicate(wand_img(frame).make_blob("png"))[0]

    result = wand_img(blob=out)
    return result

# @hook.command()
# def ggif(event, send_file, text, send_message):
#     if text == "":
#         return "See: https://github.com/sgreben/yeetgif#usage"
#     for img in event.image:
#         make_gif(text, img, send_file, send_message)


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
        def f(event, send_file, send_message):
            for img in event.image:
                args = {"effect": effect}
                img.proc_each_wand_frame(make_gif_app_caller, send_file,
                                         send_message, args)
        f.__name__ = effect

        return f

    for i in gif_effects:
        globals()[i] = hook.command()(do_func(i))


init_funcs()
