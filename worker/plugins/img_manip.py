import subprocess
from SpankyWorker import hook
from oslo_concurrency import lockutils
from wand.image import Image as wand_img
from SpankyWorker.utils.image import Image


@lockutils.synchronized("not_thread_safe")
def make_df(frame):
    frame.transform(resize="800x800>")

    frame.contrast_stretch(black_point=0.4, white_point=0.5)
    frame.modulate(saturation=800)
    frame.compression_quality = 2

    return frame


@hook.command()
def df(event, reply_file, reply):
    """
    Deepfry image
    """
    for img in event.attachments:
        img.proc_each_wand_frame(make_df, reply_file, reply)

        # Only process one frame
        return


@lockutils.synchronized("not_thread_safe")
def make_flip(frame):
    frame.flip()
    return frame


@hook.command()
def flip(event, reply_file, reply):
    """
    Flip image horizontally
    """
    for img in event.attachments:
        img.proc_each_wand_frame(make_flip, reply_file, reply)

        # Only process one frame
        return


@lockutils.synchronized("not_thread_safe")
def make_resize(frame, width, height):
    frame.resize(width, height)
    return frame


@hook.command(params="int:width int:height")
def resize(event, reply_file, reply, cmd_args):
    """
    Resize image
    """
    for img in event.attachments:
        img.proc_each_wand_frame(make_resize, reply_file, reply, cmd_args)

        # Only process one frame
        return


@lockutils.synchronized("not_thread_safe")
def make_flop(frame):
    frame.flop()
    return frame


@hook.command()
def flop(event, reply_file, reply):
    """
    Flip image vertically
    """
    for img in event.attachments:
        img.proc_each_wand_frame(make_flop, reply_file, reply)

        # Only process one frame
        return


@lockutils.synchronized("not_thread_safe")
def make_implode(frame, amount):
    print(amount)
    frame.implode(amount)
    return frame


@hook.command(params="float:amount=0.5")
def implode(event, reply_file, reply, cmd_args):
    """
    Implode image
    """
    for img in event.attachments:
        img.proc_each_wand_frame(make_implode, reply_file, reply, cmd_args)

        # Only process one frame
        return


def make_negate(frame):
    frame.negate()
    return frame


@hook.command()
def negate(event, reply_file, reply):
    """
    Invert colors
    """
    for img in event.attachments:
        img.proc_each_wand_frame(make_negate, reply_file, reply)

        # Only process one frame
        return


def make_imgtext(frame, text):
    frame.transform(resize="400x400>")

    proc = subprocess.Popen(
        ["gif", "text", text], stdin=subprocess.PIPE, stdout=subprocess.PIPE
    )

    out = proc.communicate(wand_img(frame).make_blob("png"))[0]

    result = wand_img(blob=out)
    return result


@hook.command(params="string:text")
def img_text(event, reply_file, reply, cmd_args):
    """
    Add text to image
    """
    for img in event.attachments:
        img.proc_each_wand_frame(make_imgtext, reply_file, reply, cmd_args)

        # Only process one frame
        return


def make_gif_app_caller(frame, effect):
    frame.transform(resize="400x400>")

    proc = subprocess.Popen(
        ["gif", effect], stdin=subprocess.PIPE, stdout=subprocess.PIPE
    )

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
    "cat",
]


def init_funcs():
    def do_func(effect):
        def f(event, reply_file, reply):
            for img in event.attachments:
                args = {"effect": effect}
                img.proc_each_wand_frame(
                    make_gif_app_caller, reply_file, reply, args
                )

                # Only process one frame
                return

        f.__name__ = effect

        return f

    for i in gif_effects:
        globals()[i] = hook.command()(do_func(i))


init_funcs()
