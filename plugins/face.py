import numpy as np
import face_recognition
import json
import requests
import glob
import random
import os
import string

from PIL import Image, ImageDraw
from math import hypot, sin, cos
from spanky.plugin import hook

def get_angle(p1, p2):
    dY = p1[1] - p2[1]
    dX = p1[0] - p2[0]
    return np.degrees(np.arctan2(dY, dX)) - 180

def dist_ab(p1,p2):
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

def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

def send_img_reply(img, send_file, is_gif, storage_loc):
    if is_gif:
        ext = ".gif"
    else:
        ext = ".png"

    os.system("mkdir -p " + storage_loc)
    fname = id_generator() + ext
    img.save(open(storage_loc + fname, "wb"))

    send_file(open(storage_loc + fname, 'rb'))

    os.system("rm %s/%s" % (storage_loc, fname))

@hook.command()
def glasses(event, send_file, storage_loc, send_message):
    for url in event.url:
        overlay = random.choice(glob.glob("plugin_data/face_res/glasses/*.png"))

        r = requests.get(url, stream=True)
        r.raw.decode_content = True

        out = add_glasses(Image.open(r.raw).convert("RGB"), overlay)

        if out:
            send_img_reply(out, send_file, False, storage_loc)
        else:
            send_message("No face found")

def add_glasses(image, glasses_img, debug=False):
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
        glasses = glasses.resize((int(glasses.size[0] / x_scale_ratio), int(glasses.size[1] / x_scale_ratio)))

        # Calculate where to paste the glasses
        glasses_paste = (eyes_avg[0] - glasses.size[0] // 2, eyes_avg[1] - glasses.size[1] // 2)

        image.paste(glasses, glasses_paste, glasses)

    if modified:
        return image
    else:
        return None

@hook.command()
def moustache(event, send_file, storage_loc, send_message):
    for url in event.url:
        overlay = random.choice(glob.glob("plugin_data/face_res/moustache/*.png"))

        r = requests.get(url, stream=True)
        r.raw.decode_content = True

        out = add_moustache(Image.open(r.raw).convert("RGB"), overlay)

        if out:
            send_img_reply(out, send_file, False, storage_loc)
        else:
            send_message("No face found")

def add_moustache(image, moustache_img, debug=False):
    # Find all facial features in all the faces in the image
    face_landmarks_list = face_recognition.face_landmarks(np.array(image))

    if debug:
        print("I found {} face(s) in this photograph.".format(len(face_landmarks_list)))

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
                                      int(moustache.size[1] / x_scale_ratio)))

        avg_pos = get_average_pos(face_landmarks["nose_tip"] + face_landmarks["top_lip"])

        offset = rotate_origin_only((moustache_json["offset_x"], moustache_json["offset_y"]), lip_angle)

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

@hook.command()
def hat(event, send_file, storage_loc, send_message):
    for url in event.url:
        overlay = random.choice(glob.glob("plugin_data/face_res/hat/*.png"))

        r = requests.get(url, stream=True)
        r.raw.decode_content = True

        out = add_hat(Image.open(r.raw).convert("RGB"), overlay)

        if out:
            send_img_reply(out, send_file, False, storage_loc)
        else:
            send_message("No face found")

def add_hat(image, hat_img, debug=False):
    # Find all facial features in all the faces in the image
    face_landmarks_list = face_recognition.face_landmarks(np.array(image))

    if debug:
        print("I found {} face(s) in this photograph.".format(len(face_landmarks_list)))

    hat = Image.open(hat_img)
    hat_json = json.load(open(hat_img + ".json"))

    modified = False
    # Cycle through each face
    for face_landmarks in face_landmarks_list:
        modified = True
        chin = face_landmarks["chin"]

        # Get angle - if face is rotated
        chin_angle = get_angle(chin[0], chin[-1])

        # Get size
        chin_sizex = dist_ab(chin[0], chin[-1])

        # Rotate the moustache
        hat = hat.rotate(-chin_angle, expand=True)

        # Calculate the scaling
        x_scale_ratio = hat.size[0] / chin_sizex / hat_json["scale"]

        # Resize the glasses
        hat = hat.resize((int(hat.size[0] / x_scale_ratio),
                          int(hat.size[1] / x_scale_ratio)))

        avg_pos = get_average_pos((chin[0], chin[-1]))
        print(-chin_angle)

        offset = rotate_origin_only((hat_json["offset_x"], hat_json["offset_y"]), -chin_angle)

        moustache_paste = (avg_pos[0] - hat.size[0] // 2 + offset[0],
                           avg_pos[1] - hat.size[1] // 2 + offset[1])

        image.paste(hat, moustache_paste, hat)

        if debug:
            ImageDraw.Draw(image).polygon(face_landmarks["chin"])

    if modified:
        return image
    else:
        return None
