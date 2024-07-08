import os
import uuid
import random
import json
import time
import urllib.request
import urllib.parse

from spanky.plugin import hook
from spanky.utils import discord_utils as dutils
from spanky.hook2 import (
    Hook,
    ComplexCommand,
)

server_address = None

def queue_prompt(prompt):
    p = {
        "prompt": prompt, 
        "client_id": str(uuid.uuid4())
    }
    
    data = json.dumps(p).encode('utf-8')
    req =  urllib.request.Request(f"http://{server_address}/prompt", data=data)
    
    return json.loads(urllib.request.urlopen(req).read())

def get_image(filename, subfolder, folder_type):
    data = {
        "filename": filename, 
        "subfolder": subfolder, 
        "type": folder_type
    }
    
    url_values = urllib.parse.urlencode(data)
    with urllib.request.urlopen(f"http://{server_address}/view?{url_values}") as response:
        return response.read()

def get_history(prompt_id):
    with urllib.request.urlopen(f"http://{server_address}/history/{prompt_id}") as response:
        return json.loads(response.read())

def get_images(prompt_id, max_wait=120):
    images_output = []
    while True:
        history = get_history(prompt_id)
        if history == {}:
            print(f"Waiting for prompt to finish... {max_wait} seconds left")
            time.sleep(1)

            if max_wait <= 0:
                print("Timeout")
                raise Exception("Timeout")

            continue

        prompt_history = history[prompt_id]
        for _ in prompt_history['outputs']:
            for node_id in prompt_history['outputs']:
                node_output = prompt_history['outputs'][node_id]
                
                if 'images' not in node_output:
                    continue

                for image in node_output['images']:
                    image_data = get_image(image['filename'], image['subfolder'], image['type'])
                    images_output.append(image_data)

        return images_output


def clean_string(s):
    if s == None:
        return ""
    
    return s.replace("\\", "").replace("\"", "").replace("\'", "")

@hook.on_start()
def get_server_address(bot):
    global server_address
    server_address = bot.config.get("comfyui_server_address", server_address)


hook = Hook("igen")
igen = ComplexCommand(hook, "igen")

@igen.subcommand(params="string:prompt string:negative_prompt")
async def igen_t2i(text, async_send_message, event, cmd_args):
    """
    <prompt> <negative_prompt> - Generate an image from text. Use quotes if you want to use spaces in the prompt.
    """
    prompt_text = open("plugin_data/comfyui/text2img.json.template", "r").read()

    input_prompt = clean_string(cmd_args.get("prompt", ''))
    input_negative_prompt = clean_string(cmd_args.get("negative_prompt", ''))

    # Prepare the json
    seed = random.randint(0, 100000000)
    to_replace = {
        "T_SPANKYBOT_SEED": seed,
        "T_SPANKYBOT_TEXT": input_prompt,
        "T_SPANKYBOT_NEGATIVE": input_negative_prompt
    }
    for key in to_replace:
        prompt_text = prompt_text.replace(key, str(to_replace[key]))
    prompt = json.loads(prompt_text)

    # Queue the prompt
    queue_response = queue_prompt(prompt)
    prompt_id = queue_response['prompt_id']

    # Wait for the prompt to finish
    images = get_images(prompt_id)
    if len(images) == 0:
        return "No images generated"
    
    # Save the image to a file
    filename = dutils.fname_generator() + ".png"
    with open(filename, "wb") as f:
        f.write(images[0])

    embed = dutils.prepare_embed(
        title="Text to image",
        description=text,
        image_url="attachment://" + filename,
        fields={
            "Author": event.msg.author.name,
            "Prompt": input_prompt,
            "Negative prompt": input_negative_prompt,
            "Seed": seed
        }
    )

    # Send the file
    await async_send_message(
        with_file=filename, 
        embed=embed,
        reply_to=event.msg,
        check_old=False)

    # Remove the file
    os.remove(filename)