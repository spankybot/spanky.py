from spanky.plugin import hook
from spanky.plugin.permissions import Permission
import requests
import os
import random
import string

def save_picture(url, tag_name, message, storage, storage_loc):
    if tag_name in storage.keys():
        message("%s already exists!" % tag_name)
        return

    name = ''.join(random.choice(string.ascii_letters + string.digits) for i in range(10))
    ext = url.split(".")[-1]

    try:
        fname = name + "." + ext
        os.system("mkdir -p %s" % storage_loc)
        f = open(storage_loc + fname, "wb")
        f.write(requests.get(url).content)
        f.close()

        storage[tag_name] = {}
        storage[tag_name]["type"] = "picture"
        storage[tag_name]["location"] = fname

        storage.sync()

        message("Added picture tag")
    except:
        del storage[tag_name]
        import traceback
        traceback.print_exc()

def save_text(text_list, tag_name, message, storage):
    if tag_name in storage.keys():
        message("already exists")
        return

    os.makedirs("tags", exist_ok=True)

    try:
        storage[tag_name] = {}
        storage[tag_name]["type"] = "text"
        storage[tag_name]["content"] = " ".join(i for i in text_list)
        storage.sync()

        message("Added text tag")
    except:
        del storage[tag_name]
        storage.sync()

        import traceback
        traceback.print_exc()

@hook.command()
def tag(text, send_file, storage, storage_loc):
    """
    <tag> - Return a tag.
    """
    text = text.split()
    if len(text) == 0:
        return __doc__

    tag = text[0]

    if tag == "list":
        return "Tags: `" + ", ".join(i for i in sorted(list(storage))) + "`"
    else:
        if tag in storage:
            if storage[tag]['type'] == "text":
                return storage[tag]['content']
            elif storage[tag]['type'] == "picture":
                send_file(open(storage_loc + storage[tag]['location'], 'rb'))
        else:
            return "Syntax is: `.tag list` or `.tag <name>`"

@hook.command()
def tag_add(text, event, reply, storage, storage_loc):
    """
    <identifier content> - add tag content as indentifier
    """
    text = text.split()
    if len(event.attachments) > 0:
        if len(text) != 1:
            return 'Format is: `.tag_add <name> picture`'

        save_picture(event.attachments[0].url, text[0], reply, storage, storage_loc)
    else:
        if len(text) < 2:
            return 'If no picture is attached, add more words'

        save_text(text[1:], text[0], reply, storage)

@hook.command(permissions=Permission.admin, format="cmd")
def tag_del(text, storage):
    """
    <tag> - delete a tag
    """
    if text not in storage.keys():
        return "%s is not a tag" % text

    if storage[text]["type"] == "picture":
        os.remove(storage[text]['location'])

    del storage[text]
    storage.sync()
    return "Done!"

