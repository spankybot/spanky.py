import numpy as np
import face_recognition
import json
import requests
import glob
import random
import PIL
import os

from PIL import Image, ImageDraw
from math import hypot, sin, cos
from core import hook


def get_angle(p1, p2):
    dY = p1[1] - p2[1]
    dX = p1[0] - p2[0]
    return np.degrees(np.arctan2(dY, dX)) - 180


def dist_ab(p1, p2):
    return hypot(p1[0] - p2[0], p1[1] - p2[1])


def avg_pos_rel_p1(p1, p2):
    return (
        p1[0] + (p2[0] - p1[0]) // 2,
        p1[1] + (p2[1] - p1[1]) // 2)


def get_average_pos(array):
    avg = np.average(array, axis=0)
    return (int(avg[0]), int(avg[1]))


def rotate_origin_only(xy, angle):
    if angle > 180:
        angle -= 360

    radians = angle / 180

    x, y = xy
    xx = x * cos(radians) + y * sin(radians)
    yy = -x * sin(radians) + y * cos(radians)

    return int(xx), int(yy)


def prepare_image(img):
    x_scale = 1
    y_scale = 1

    size_x = img.size[0]
    size_y = img.size[1]

    if size_x > 800:
        x_scale = 800 / img.size[0]
        size_x *= x_scale
        size_y *= x_scale

    if size_y > 800:
        y_scale = 800 / size_y
        size_x *= y_scale
        size_y *= y_scale

    if x_scale != 1 or y_scale != 1:
        img = img.resize((int(size_x),
                          int(size_y)), resample=PIL.Image.BICUBIC)

    return img


def get_overlay(name, location):
    """
    Get an overlay or return a random one.
    If an invalid overlay is requested, return an error.
    """

    overlay = None
    if name == "random":
        overlay = random.choice(glob.glob("%s/*.png.json" % location))
    else:
        # CHeck if the file exists
        if os.path.isfile("%s/%s.png.json" % (location, name)):
            overlay = "%s/%s.png.json" % (location, name)
        else:
            # Enumerate all resources and return
            resources = glob.glob("%s/*.png.json" % location)
            return False, "%s is not a valid parameter. Try one of: %s" % \
                (name,
                 ", ".join(i.split("/")[-1].replace(".png.json", "") for i in resources))

    return True, overlay.replace(".json", "")


@hook.command(params="string:name=random")
def glasses(event, send_file, send_message, cmd_args):
    valid, overlay = get_overlay(
        cmd_args["name"], "plugin_data/face_res/glasses/")

    if not valid:
        return overlay

    for img in event.image:
        img.proc_each_pil_frame(add_glasses, send_file, send_message, {
                                "glasses_img": overlay})


def add_glasses(image, glasses_img, debug=False):
    image = prepare_image(image)
    # Find all facial features in all the faces in the image
    face_landmarks_list = face_recognition.face_landmarks(np.array(image))

    glasses = Image.open(glasses_img)
    glasses_json = json.load(open(glasses_img + ".json"))

    modified = False
    # Cycle through each face
    for face_landmarks in face_landmarks_list:
        modified = True

        left_eye = face_landmarks["left_eye"]
        right_eye = face_landmarks["right_eye"]

        # Get average positions for the eyes
        avg_left = get_average_pos(left_eye)
        avg_right = get_average_pos(right_eye)

        # Get eyes angle - if face is rotated
        eyes_angle = get_angle(avg_left, avg_right)

        # Get distance between eyes
        eyes_dist = dist_ab(avg_left, avg_right)

        # What's the center point between the eyes
        eyes_avg = avg_pos_rel_p1(avg_left, avg_right)

        # Rotate the glasses to match the angle of the eyes
        glasses = glasses.rotate(-eyes_angle, expand=True)

        # Calculate the scaling depending on the size of the eyes relative to the glasses
        x_scale_ratio = glasses.size[0] / eyes_dist / glasses_json["scale"]

        # Resize the glasses
        glasses = glasses.resize((int(glasses.size[0] / x_scale_ratio), int(
            glasses.size[1] / x_scale_ratio)), resample=PIL.Image.BICUBIC)

        offset = rotate_origin_only(
            (glasses_json["offset_x"], glasses_json["offset_y"]), -eyes_angle)

        # Calculate where to paste the glasses
        glasses_paste = (eyes_avg[0] - glasses.size[0] // 2 +
                         offset[0], eyes_avg[1] - glasses.size[1] // 2 + offset[1])

        image.paste(glasses, glasses_paste, glasses)

    if modified:
        return image
    else:
        return None


@hook.command(params="string:name=random")
def moustache(event, send_file, send_message, cmd_args):
    valid, overlay = get_overlay(
        cmd_args["name"], "plugin_data/face_res/moustache/")

    if not valid:
        return overlay

    for img in event.image:
        img.proc_each_pil_frame(add_moustache, send_file, send_message, {
                                "moustache_img": overlay})


def add_moustache(image, moustache_img, debug=False):
    image = prepare_image(image)
    # Find all facial features in all the faces in the image
    face_landmarks_list = face_recognition.face_landmarks(np.array(image))

    if debug:
        print("I found {} face(s) in this photograph.".format(
            len(face_landmarks_list)))

    moustache = Image.open(moustache_img)
    moustache_json = json.load(open(moustache_img + ".json"))

    modified = False
    # Cycle through each face
    for face_landmarks in face_landmarks_list:
        modified = True
        top_lip = face_landmarks["top_lip"]

        # Get lip angle - if face is rotated
        lip_angle = get_angle(top_lip[0], top_lip[6])

        # Get size of lip
        lip_sizex = dist_ab(top_lip[0], top_lip[6])

        # Rotate the moustache
        moustache = moustache.rotate(-lip_angle, expand=True)

        # Calculate the scaling
        x_scale_ratio = moustache.size[0] / lip_sizex / moustache_json["scale"]

        # Resize the glasses
        moustache = moustache.resize((int(moustache.size[0] / x_scale_ratio),
                                      int(moustache.size[1] / x_scale_ratio)), resample=PIL.Image.BICUBIC)

        avg_pos = get_average_pos(
            face_landmarks["nose_tip"] + face_landmarks["top_lip"])

        offset = rotate_origin_only(
            (moustache_json["offset_x"], moustache_json["offset_y"]), -lip_angle)

        moustache_paste = (avg_pos[0] - moustache.size[0] // 2 + offset[0],
                           avg_pos[1] - moustache.size[1] // 2 + offset[1])

        image.paste(moustache, moustache_paste, moustache)

        if debug:
            for l in face_landmarks.keys():
                ImageDraw.Draw(image).polygon(face_landmarks[l])

    if modified:
        return image
    else:
        return None


@hook.command(params="string:name=random")
def hat(event, send_file, send_message, cmd_args):
    valid, overlay = get_overlay(cmd_args["name"], "plugin_data/face_res/hat/")

    if not valid:
        return overlay

    for img in event.image:
        img.proc_each_pil_frame(
            add_hat, send_file, send_message, {"hat_img": overlay})


def add_hat(image, hat_img, debug=False):
    image = prepare_image(image)

    # Find all facial features in all the faces in the image
    face_landmarks_list = face_recognition.face_landmarks(np.array(image))

    if debug:
        print("I found {} face(s) in this photograph.".format(
            len(face_landmarks_list)))

    hat = Image.open(hat_img)
    hat_json = json.load(open(hat_img + ".json"))

    modified = False
    # Cycle through each face
    for face_landmarks in face_landmarks_list:
        modified = True
        left_eye = face_landmarks["left_eye"]
        right_eye = face_landmarks["right_eye"]

        # Get average positions for the eyes
        avg_left = get_average_pos(left_eye)
        avg_right = get_average_pos(right_eye)

        # Get angle - if face is rotated
        chin_angle = get_angle(avg_left, avg_right)

        # Get size
        chin_sizex = dist_ab(avg_left, avg_right)

        # Rotate the moustache
        hat = hat.rotate(-chin_angle, expand=True)

        # Calculate the scaling
        x_scale_ratio = hat.size[0] / chin_sizex / hat_json["scale"]

        # Resize the glasses
        hat = hat.resize((int(hat.size[0] / x_scale_ratio),
                          int(hat.size[1] / x_scale_ratio)), resample=PIL.Image.BICUBIC)

        avg_pos = avg_pos_rel_p1(avg_left, avg_right)
        print(-chin_angle)

        offset = rotate_origin_only(
            (hat_json["offset_x"], hat_json["offset_y"]), -chin_angle)

        moustache_paste = (avg_pos[0] - hat.size[0] // 2 + offset[0],
                           avg_pos[1] - hat.size[1] // 2 + offset[1])

        image.paste(hat, moustache_paste, hat)

        if debug:
            ImageDraw.Draw(image).polygon(face_landmarks["chin"])

    if modified:
        return image
    else:
        return None


@hook.command(params="string:name=random")
def eyes(event, send_file, storage_loc, send_message, cmd_args):
    valid, overlay = get_overlay(
        cmd_args["name"], "plugin_data/face_res/eyes/")

    if not valid:
        return overlay

    for img in event.image:
        img.proc_each_pil_frame(add_eyes, send_file, send_message, {
                                "eyes_img": overlay})


def add_eyes(image, eyes_img, debug=False):
    image = prepare_image(image)

    # Find all facial features in all the faces in the image
    face_landmarks_list = face_recognition.face_landmarks(np.array(image))

    if debug:
        print("I found {} face(s) in this photograph.".format(
            len(face_landmarks_list)))

    eye_l = Image.open(eyes_img.replace(".png", "_l.png"))
    eye_r = Image.open(eyes_img.replace(".png", "_r.png"))
    eyes_json = json.load(open(eyes_img + ".json"))

    modified = False
    # Cycle through each face
    for face_landmarks in face_landmarks_list:
        modified = True
        left_eye = face_landmarks["left_eye"]
        right_eye = face_landmarks["right_eye"]

        # Get average positions for the eyes
        avg_left = get_average_pos(left_eye)
        avg_right = get_average_pos(right_eye)

        # Get eyes angle - if face is rotated
        eyes_angle = get_angle(avg_left, avg_right)

        # Get distance between eyes
        eyes_dist = dist_ab(avg_left, avg_right)

        # Rotate the moustache
        eye_l = eye_l.rotate(-eyes_angle, expand=True)
        eye_r = eye_r.rotate(-eyes_angle, expand=True)

        # Calculate the scaling and resize
        x_scale_ratio_l = eye_l.size[0] / eyes_dist / eyes_json["scale"]
        eye_l = eye_l.resize((int(eye_l.size[0] / x_scale_ratio_l),
                              int(eye_l.size[1] / x_scale_ratio_l)), resample=PIL.Image.BICUBIC)

        # Calculate the scaling and resize
        x_scale_ratio_r = eye_r.size[0] / eyes_dist / eyes_json["scale"]
        eye_r = eye_r.resize((int(eye_r.size[0] / x_scale_ratio_r),
                              int(eye_r.size[1] / x_scale_ratio_r)), resample=PIL.Image.BICUBIC)

        offset = rotate_origin_only(
            (eyes_json["offset_x"], eyes_json["offset_y"]), -eyes_angle)

        eye_l_paste = (avg_left[0] - eye_l.size[0] // 2 + offset[0],
                       avg_left[1] - eye_l.size[1] // 2 + offset[1])

        eye_r_paste = (avg_right[0] - eye_r.size[0] // 2 + offset[0],
                       avg_right[1] - eye_r.size[1] // 2 + offset[1])

        image.paste(eye_l, eye_l_paste, eye_l)
        image.paste(eye_r, eye_r_paste, eye_r)

    if modified:
        return image
    else:
        return None
