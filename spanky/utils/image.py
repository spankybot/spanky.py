import wand
import os
import string
import random
import requests
import time
import PIL
import re
import io
from wand.image import Image as wand_image
from wand.image import Color as wand_color
from wand.resource import limits
from wand.sequence import SingleImage

from PIL import Image as pil_image
from PIL import ImageSequence as pil_imagesequence
from PIL import ImageDraw as pil_imagedraw
from PIL import GifImagePlugin

MAX_IMG_SIZE = 10 * 1024 * 1024
MAX_RES_SIZE = 1024 * 1024 * 1024


class Image:
    def __init__(self, url=None, raw_data=None):
        """
        Creates an object that holds raw data and can create a wand or PIL image
        """
        if raw_data:
            self._raw = [raw_data]
        else:
            self._raw = []

        self._wand = None
        self._pil = None
        self._url = url
        self._first_frame_sz = 0

    @property
    def url(self):
        return self._url

    def append(self, img_data):
        """
        Append a frame to the raw data
        """
        print("Appending frame - length %d" % len(self._raw))
        self._raw.append(img_data)

    def get_first_frame_sz(self):
        """
        Return the estimated size, based on the size of the first frame
        """
        # Get the first frame size
        if self._first_frame_sz == 0:
            self._first_frame_sz = self.get_crt_size()

        return self._first_frame_sz

    def append_img(self, img):
        """
        Append an image that may contain multiple frames
        """
        for frame in img.sequence:
            self.append(frame)

    def extend(self, img_list):
        """
        Extend the raw data with a list of frames
        """
        for img in img_list:
            self.append(img)

    def set_raw_data(self, raw):
        """
        Set the raw data to something predefined
        """
        self._raw = [raw]

    def wand(self):
        """
        Create a wand image
        """

        # If no raw data exists, fetch the url
        if len(self._raw) == 0:
            self.fetch_url()
            self._wand = wand_image(blob=self._raw[0])

        if self._wand == None:
            # Create a dummy image
            self._wand = wand_image()

            # For each frame, append it to a sequence
            for frame in self._raw:
                self._wand.sequence.append(frame)

        return self._wand

    def get_crt_size(self):
        """
        Returns the current size of the image as if saved on disk
        """
        # Create a temporary image
        temp_img = wand_image()
        for frame in self._raw:
            temp_img.sequence.append(frame)

        # Save it to memory
        ibytes = io.BytesIO()
        temp_img.save(file=ibytes)
        temp_img.destroy()

        return ibytes.getbuffer().nbytes

    def clean_data(self):
        """
        Clean up allocated wand images
        """
        for frame in self._raw:
            if type(frame) == SingleImage or type(frame) == wand_image:
                frame.destroy()

        while self._wand != None and len(self._wand.sequence) > 0:
            try:
                self._wand.sequence.pop().destroy()
            except:
                pass

        try:
            self._wand.destroy()
        except:
            pass

    def pil(self):
        """
        Create a PIL image
        """

        if len(self._raw) == 0:
            self.fetch_url()

        if self._pil == None:
            self._pil = pil_image.open(io.BytesIO(self._raw[0]))

        return self._pil

    def proc_imgur(self, starturl):
        """
        Process an imgur link
        """

        # If imgur is not in the link, skip it
        if "imgur.com" not in starturl:
            return starturl

        finishedurl = []
        regex = (
            r"href\=\"https://i\.imgur\.com\/([\d\w]*)(\.jpg|\.png|\.gif|\.mp4|\.gifv)"
        )
        try:
            imgurHTML = requests.get(starturl)
        except:
            raise Exception("Something failed with the download")

        # Try finding all the embedded imgur links
        imgurhash = re.findall(regex, imgurHTML.text)

        # If no embedded links have been found, return the original url
        if len(imgurhash) == 0:
            return starturl

        finishedurl.append(
            "https://i.imgur.com/{0}{1}".format(imgurhash[0][0], imgurhash[0][1])
        )
        return finishedurl

    def fetch_url(self, timeout_sec=60, max_size=1024 * 1024 * 20):
        """
        Fetch the class set url
        """
        url = self.proc_imgur(self._url)

        req = requests.get(url, stream=True)
        req.raise_for_status()

        size = 0
        start = time.time()

        content = bytes()
        # Get a chunk
        for chunk in req.iter_content(1024):
            # If download time exceeds the given timeout, exit
            if time.time() - start > timeout_sec:
                print("Image %s took too long to download" % url)
                raise TimeoutError("Timeout error downloading %s" % url)

            content += chunk
            size += len(chunk)

            # If the size eceeds the given maximum size, exit
            if size > max_size:
                print("Image %s is too large" % url)
                raise PermissionError("Image too large")

        self.set_raw_data(content)

    def print_memusage(self, text):
        """
        Print memory usage, based on the information given by the wand module
        """
        memory_mb = int(limits.resource("memory")) / 1024 / 1024
        print("[%s] Using %d" % (text, memory_mb))

    def fname_generator(self, size=6, chars=string.ascii_uppercase + string.digits):
        """
        Generate a random string containing uppercase ascii and digits
        """
        return "".join(random.choice(chars) for _ in range(size))

    def send_img_reply(self, send_file):
        """
        Send generated image as a reply
        """

        # If the raw data contains multiple frames, it's a gif
        if type(self._raw) == list and len(self._raw) > 1:
            ext = ".gif"
        else:
            ext = ".png"

        storage_loc = "temp-upload/"

        os.system("mkdir -p %s" % storage_loc)
        # TODO Use BytesIO
        fname = self.fname_generator() + ext
        self.wand().save(filename=storage_loc + fname)
        send_file(storage_loc + fname)

        os.system("rm %s/%s" % (storage_loc, fname))

    def check_size(self, frame_count):
        """
        Check resource limits
        """

        # If estimated size is larger than the maximum image size, then raise
        if self.get_first_frame_sz() * frame_count > MAX_IMG_SIZE:
            print(
                "Abort because frame size is %d and frame count is %d"
                % (self.get_first_frame_sz(), frame_count)
            )
            raise

        # If memory consumption for the wand module is too large, exit
        if limits.resource("memory") > MAX_RES_SIZE:
            raise

    def proc_each_wand_frame(self, func, send_file, send_msg, args={}):
        """
        Calls func for each wand frame
        """

        new_img = Image()
        self.print_memusage("Before start")
        try:
            send_msg("Working...")
            for idx, frame in enumerate(self.wand().sequence):
                print("Processing frame %d" % idx)
                # For each frame, call the image processor
                self.print_memusage("Before func call")
                result = func(frame, **args)
                self.print_memusage("After func call")

                # Append it to the results
                if type(result) == list:
                    new_img.extend(result)
                elif type(result) == wand_image:
                    new_img.append_img(result)
                    try:
                        while True:
                            result.sequence.pop()
                    except:
                        pass
                    result.destroy()
                else:
                    new_img.append(result)

                # Check if we're not consuming too much memory
                new_img.check_size(idx + 1)

                self.print_memusage("After append")

            # Send the reply
            new_img.send_img_reply(send_file)
        except:
            import traceback

            traceback.print_exc()
            send_msg("Something didn't work.")
        finally:
            new_img.clean_data()

        self.clean_data()
        self.print_memusage("After finish")

    def proc_each_pil_frame(self, func, send_file, send_msg, args={}):
        new_img = Image()
        self.print_memusage("Before start")
        try:
            send_msg("Working...")
            img = self.pil()

            modified_frames = False
            for idx, frame in enumerate(pil_imagesequence.Iterator(img)):
                # For each frame, call the image processor
                result = func(frame.convert("RGB"), **args)
                if result != None:
                    modified_frames = True
                else:
                    result = frame

                # Append it to the results
                ibytes = io.BytesIO()
                result.save(ibytes, "PNG")

                ibytes.seek(0)
                new_img.append(wand_image(file=ibytes))

                # Check if we're not consuming too much memory
                new_img.check_size(idx + 1)

            if modified_frames:
                new_img.send_img_reply(send_file)
            else:
                send_msg("No frames changed. Not returning anything")
        except:
            import traceback

            traceback.print_exc()
            send_msg("Something didn't work.")
        finally:
            new_img.clean_data()

        self.clean_data()
        self.print_memusage("After finish")
