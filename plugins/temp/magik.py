import wand
import os
import string
import random
import time
import subprocess
from core import hook
from utils.image import Image
from wand.image import Color
from wand.image import Image as wand_image
from oslo_concurrency import lockutils


@lockutils.synchronized('not_thread_safe')
def make_magik(frame, ratio1=0.5, ratio2=1.5):
    frame.transform(resize='800x800>')
    scale = 0

    print(ratio1)

    frame.liquid_rescale(
        width=int(frame.width * ratio1),
        height=int(frame.height * ratio1),
        delta_x=int(0.5 * scale) if scale else 1, rigidity=0)

    frame.liquid_rescale(
        width=int(frame.width * ratio2),
        height=int(frame.height * ratio2),
        delta_x=scale if scale else 2, rigidity=0)

    return frame


@lockutils.synchronized('not_thread_safe')
def make_gmagik(frame, ratio1=0.5, ratio2=1.5, frames=10):
    global wand_image

    frame.transform(resize='400x400>')
    frame.background_color = Color('black')
    frame.alpha_channel = 'remove'

    orig_width = frame.width
    orig_height = frame.height

    result = wand_image()
    for i in range(frames):
        frame.liquid_rescale(
            width=int(frame.width * ratio1),
            height=int(frame.height * ratio1),
            delta_x=1, rigidity=0)

        frame.liquid_rescale(
            width=int(frame.width * ratio2),
            height=int(frame.height * ratio2),
            delta_x=2, rigidity=0)

        frame.resize(orig_width, orig_height)
        result.sequence.append(frame)
    return result


@hook.command(params="float:ratio1=0.5 float:ratio2=1.5")
def magik(event, send_file, send_message, cmd_args):
    for img in event.image:
        img.proc_each_wand_frame(make_magik, send_file, send_message, cmd_args)


@hook.command(params="int:frames=10 float:ratio1=0.8 float:ratio2=1.2")
def gmagik(event, send_file, send_message, cmd_args):
    for img in event.image:
        img.proc_each_wand_frame(
            make_gmagik, send_file, send_message, cmd_args)
