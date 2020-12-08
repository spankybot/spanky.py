from PIL import Image
import requests
import random
import os
from spanky.plugin import hook
from spanky.plugin.permissions import Permission
import discord
import io
import json
import asyncio

SERVERS = [
    "287285563118190592", # Roddit
    "648937029433950218", # CNC's own test server
    "297483005763780613", # plp's magic test server
]

# For any future archeologist digging up this code, I used PERMS because I didnt want to bother people with adding command owners to the administration commands
# Signed, CNC, Bot owner but not Admin on Roddit
PERMS = [Permission.admin, Permission.bot_owner]

image_path = "plugin_data/christmas_banner/%s"
emoji_path = "plugin_data/christmas_ornaments/%s"

active_trees = {}

MSG_TIMEOUT = 5

star_position = (384,-10)
star_URL = "http://www.pngall.com/wp-content/uploads/2017/05/Star-PNG-File.png"
star_ornament = None
prefix_URL = "https://cdn.discordapp.com/emojis/"

emoji_cache = {}

# Required administrative perms: Manage Emoji, ???

@hook.command(server_id=SERVERS, aliases=["ornate", "ornamentare", "ornament"], format="ornament")
def ornare(storage, event, text):
    """ornare <ornament> - Ornează bradul. Dacă încerci să ornezi de mai multe ori, doar cel pus acum va fi păstrat."""
    if not storage["is_active"]:
        return "Nu suntem în sezon"
    
    tree = active_trees[str(event.server.id)]
    if tree.concluded:
        return "Evenimentul s-a încheiat, vă mulțumim pentru participare!"

    url = [url for url in event.url]
    if url == []:
        return "N-ai specificat ornament"
    url = url[0]

    # check if URL meets restricted checks
    if storage["restricted"] and not good_ornament(url, storage):
        return "Nu e ok ornamentul"

    if not url.startswith(prefix_URL):
        return "Nu mai încerca să exploatezi <:xciudat:782909461957967935>"

    end_text = "Am ornat bradul"
    if not storage["unlimited"] and str(event.author.id) not in storage["unlimited_adders"] and tree.has_ornament(str(event.author.id)):
        tree.remove_ornaments(str(event.author.id))
        end_text = "Am reornat bradul"

    tree.create_ornament(url, owner_id=event.author.id)
    sync_tree(sv_id=event.server.id, storage=storage)

    return end_text

@hook.command(server_id=SERVERS, permissions=PERMS, format="username")
def assign_special_user(storage, event, text, str_to_id):
    """Selectați un utilizator special care să încheie evenimentul!"""
    u_id = str_to_id(text)
    storage["special_user"] = u_id
    return "Am setat userul special"

@hook.command(server_id=SERVERS)
def ornare_stea(storage, event):
    """Finalul evenimentului. Doar un user special poate face asta!"""
    if str(event.author.id) != storage["special_user"]:
        return
    if not storage["is_active"]:
        return "Nu suntem în sezon"
    tree = active_trees[str(event.server.id)]
    if tree.concluded:
        return "Evenimentul s-a încheiat, vă mulțumim pentru participare!"
    tree.finish()
    tree.add_ornament(star_ornament, update=True)
    sync_tree(sv_id=event.server.id, storage=storage)
    return "Am ornat bradul cu steaua!"

@hook.command(server_id=SERVERS, permissions=PERMS)
def clear_ornaments(event, storage):
    """Șterge toate ornamentele de pe copac. Dacă a fost pusă steaua, evenimentul reîncepe"""
    tree = active_trees[str(event.server.id)]
    tree.concluded = False
    tree.clear_ornaments()
    sync_tree(sv_id=event.server.id, storage=storage)
    return "Done."

@hook.command(server_id=SERVERS, permissions=PERMS)
def start_christmas(bot, storage, event):
    """Începe Crăciunul. Activează toate comenzile din roddit_christmas."""
    if storage["is_active"]:
        return "Christmas already started"
    storage["is_active"] = True 
    storage["tree"]["concluded"] = False
    storage.sync()
    
    ChristmasTree.deserialize(bot, storage, event.server)

    return "Started Christmas"

@hook.command(server_id=SERVERS, permissions=PERMS)
def end_christmas(event, storage):
    """Oprește Crăciunul. Ornamentele rămân salvate pentru când începeți din nou."""
    if not storage["is_active"]:
        return "Crăciunul deja a luat sfârșit"
    storage["is_active"] = False 
    storage.sync()
    
    active_trees.pop(event.server.id)

    return "Am terminat Crăciunul"

@hook.command(server_id=SERVERS, permissions=PERMS)
async def get_tree(event, async_send_file, reply, storage):
    """Primește imaginea bradului. Fiindcă e operație intensivă, e limitată doar adminilor"""
    if not storage["is_active"]:
        reply("Nu a început Crăciunul")
        return
    sid = str(event.server.id)
    
    img = active_trees[sid].get_image()
    bio = io.BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)

    dfile = discord.File(bio, "tree.png")
    await async_send_file(dfile)

@hook.command(server_id=SERVERS, permissions=PERMS)
def restrict_ornaments(event, storage):
    """Restrânge lista de ornamente permise la cele adăugate de bot pentru eveniment."""
    storage["restricted"] = True
    storage.sync()
    return "Restricted."

@hook.command(server_id=SERVERS, permissions=PERMS)
def unrestrict_ornaments(event, storage):
    """Elimină limitarea de ornamente. Recomand să nu o utilizați"""
    storage["restricted"] = False
    storage.sync()
    return "Restricted."

@hook.command(server_id=SERVERS, permissions=PERMS)
def toggle_update_christmas_banner(event, storage):
    """Comută starea actualizării banner-ului"""
    if not storage["is_active"]:
        return "N-a început Crăciunul"
    if not event.server.can_have_banner:
        return "Acest server nu poate avea banner"
    
    tree = active_trees[str(event.server.id)]
    tree.banner = not tree.banner
    sync_tree(sv_id=event.server.id, storage=storage)
    
    if tree.banner:
        return "Am pornit actualizarea banner-ului"
    return "Am oprit actualizarea banner-ului"

# add_emoji and remove_emoji assume that you don't remove the stuff from plugin_data/christmas_ornaments
@hook.command(server_id=SERVERS, permissions=PERMS)
async def add_emoji(event, storage, bot, reply):
    """Adaugă ornamentele de Crăciun ale botului. NOTE: Este o operație lentă, emoji-urile fiind puse unul după altul"""
    with open(emoji_path % "data.json", "r") as f:
        data = json.load(f)
        for orn in data:
            if 'filename' in orn and not ornament_exists(orn["filename"], storage):
                with open(emoji_path % orn["filename"], "rb") as fp:
                    print("Adding %s / %s" % (orn["filename"], orn["emoji_name"]))
                    em = await event.server.add_emoji(fp=fp.read(), name=orn["emoji_name"])
                    storage["allowed_emoji"].append({"discord_id": em.id, "local_name": orn["filename"]})
                    storage.sync()
                    print("Added.")
    reply("Added emoji, enjoy!")

@hook.command(server_id=SERVERS, permissions=PERMS)
async def remove_emoji(bot, event, storage, reply):
    """Curățenie de primăvară a emoji-urilor botului."""
    for emoji in storage["allowed_emoji"]:
        em = event.server.get_emoji(emoji["discord_id"])
        if em:
            await em.delete()
    storage["allowed_emoji"] = []
    storage.sync()
    reply("S-a terminat curățenia de primăvară")


@hook.command(server_id=SERVERS, permissions=PERMS)
def toggle_unlimited_adding(storage, text, str_to_id):
    """Comută dacă toți userii pot avea mai multe ornamente aplicate pe brad"""
    storage["unlimited"] = not storage["unlimited"]
    storage.sync()
    return "Done, set to %s" % storage["unlimited"]

@hook.command(server_id=SERVERS, permissions=PERMS)
def add_unlimited_adder(storage, text, str_to_id):
    """Adaugă user care poate adăuga oricâte ornamente vrea el. Comandă făcută pentru testare"""
    u_id = str(str_to_id(text))
    if u_id in storage["unlimited_adders"]:
        return "Userul deja poate adăuga nelimitat"
    storage["unlimited_adders"].append(u_id)
    storage.sync()
    return "Done."

@hook.command(server_id=SERVERS, permissions=PERMS)
def remove_unlimited_adder(storage, text, str_to_id):
    """Șterge user care poate adăuga oricâte ornamente vrea el. Comandă făcută pentru testare"""
    u_id = str(str_to_id(text))
    if u_id not in storage["unlimited_adders"]:
        return "Userul oricum nu poate adăuga nelimitat"
    storage["unlimited_adders"].remove(u_id)
    storage.sync()
    return "Done."

@hook.command(server_id=SERVERS, permissions=PERMS)
def christmas_info(storage, event):
    """Informații utile despre cum merge evenimentul. Nu utilizați într-un canal public"""
    base = f"""
Is Active? {storage["is_active"]}
Restricted Emoji? {storage["restricted"]}
Allowed Emoji: {["<:test:%s>"%emoji["discord_id"] for emoji in storage["allowed_emoji"]]}
Unlimited Adding? {storage["unlimited"]}
Unlimited Adders: {["<@%s>" % user_id for user_id in storage["unlimited_adders"]]}
Special User: <@{storage["special_user"]}>
"""
    if str(event.server.id) in active_trees:
        tree = active_trees[str(event.server.id)]
        base += f"""----------
Tree info:
----------
Set Banner? {tree.banner}
Number of Ornaments: {len(tree.ornaments)}
Concluded? {tree.concluded}
"""
    return base

# ChristmasTree is the main class, from which we can get everything
class ChristmasTree:
    # `image` is a PIL image representing the base image 
    # `ornaments` is the dict that has the data from the `/plugin_data/christmas_ornaments/info.json` file
    def __init__(self, image, mask, ornaments, server, banner, concluded):
        self.img = image.convert('RGBA')
        self.points = [] # points on which we can put the center of an ornament
        self.server = server
        self.banner = banner
        self.concluded = concluded

        self.ornaments = [] 

        if mask:
            self.load(mask)
        if ornaments:
            self.load_ornaments(ornaments)

    # `mask` is a black-and-white PIL image from which we will get self.points
    def load(self, mask, treshold=128):
        print("Loading tree")
        self.points = []
        mask = mask.convert('LA')
        px = mask.load()
        for i in range(mask.width):
            for j in range(mask.height):
                if px[i,j][1] > treshold: # random value, but transparent
                    self.points.append((i,j))

    def serialize(self):
        elem = {}
        elem["ornaments"] = self.dump_ornaments()
        elem["banner"] = self.banner
        elem["concluded"] = self.concluded
        return elem 

    @staticmethod
    def deserialize(bot, storage, server):
        # Don't rebuild inactive trees
        if not storage["is_active"]:
            return None

        if str(server.id) in active_trees:
            active_trees.pop(str(server.id))

        full_path = "plugin_data/christmas_banner/image.png"
        mask_path = "plugin_data/christmas_banner/mask.png"
        img = Image.open(full_path)
        mask = Image.open(mask_path)
        
        tree = ChristmasTree(image=img, 
                             mask=mask, 
                             server=server, 
                             ornaments=storage["tree"]["ornaments"], 
                             banner=storage["tree"]["banner"], 
                             concluded=storage["tree"]["concluded"])

        active_trees[str(server.id)] = tree

        return tree

    # update triggers an update
    def update(self):
        print("Updating tree")
        if self.banner and self.server.can_have_banner:
            bio = io.BytesIO()
            self.get_image().save(bio, 'PNG')
            bio = bio.getvalue()
            self.server.set_banner(bio)
    
    # get_image pastes all ornaments on the image and returns the resulting image
    def get_image(self):
        img = self.img.copy()
        for ornament in self.ornaments:
            o_image = ornament.get_image() 
            
            pos = ornament.get_position()
            pos = (pos[0] - o_image.width // 2, pos[1])
            img.paste(o_image, box=pos, mask=o_image)
        return img

    # add_ornament adds an arbitrary pre-created ornament
    def add_ornament(self, ornament, update=False):
        self.ornaments.append(ornament)
        if update:
            self.update()
    
    # load_ornaments loads the ornaments from a dict created by dump_ornaments
    def load_ornaments(self, data):
        for i in data:
            ornament = Ornament.deserialize(i)
            if not ornament:
                print("Invalid ornament, plz fix:", i)
                continue
            self.add_ornament(ornament)

        if len(data) > 0:
            self.update()

    # dump_ornaments returns the dict for all ornaments, to be stored somewhere 
    def dump_ornaments(self):
        d = []
        for ornament in self.ornaments:
            d.append(ornament.serialize())
        return d

    def clear_ornaments(self):
        self.ornaments = []
        self.update()
    
    def random_angle(self):
        return round(random.uniform(-45, 45), 2)

    def random_position(self):
        return random.choice(self.points)

    def create_ornament(self, url, owner_id="", max_w=50, update=True):
        angle = self.random_angle()
        position = self.random_position()
        self.add_ornament(ornament=Ornament(url=url, 
                                            angle=angle,
                                            position=position,
                                            owner_id=owner_id,
                                            max_w=max_w), update=True)

    def has_ornament(self, owner_id):
        for orn in self.ornaments:
            if orn.owner_id == owner_id:
                return True
        return False

    def remove_ornaments(self, owner_id):
        self.ornaments = [orn for orn in self.ornaments if orn.owner_id != owner_id]

    @property
    def sid(self):
        return str(self.server.id)

    def finish(self):
        self.concluded = True

class Ornament:
    # `url` is the url to an image
    def __init__(self, position, angle, url, owner_id="", max_w=50):
        self.owner_id = owner_id
        self.position = position
        self.angle = angle
        self.max_w = max_w
        self.url = str(url)
        self.img = None
        self.load_image()
        self.rotate_image()
    
    def get_position(self):
        return self.position

    def get_angle(self):
        return self.angle

    @staticmethod
    def deserialize(data):
        try:
            angle = data["angle"]
            position = data["position"]
            url = data["url"]
            max_w = data["max_w"]
            owner_id = data["owner_id"]
            return Ornament(angle=angle,
                            position=position, 
                            url=url, 
                            max_w=max_w, 
                            owner_id=owner_id)
        except KeyError:
            print("Invalid ornament data:", data)
        return None 
    
    def serialize(self):
        d = {}
        d["position"] = self.position 
        d["angle"] = self.angle
        d["url"] = self.url
        d["max_w"] = self.max_w
        d["owner_id"] = self.owner_id
        return d

    def load_image(self):
        if self.url in emoji_cache:
            self.img = emoji_cache[self.url].copy()
            return
        resp = requests.get(self.url, stream=True)
        resp.raw.decode_content = True 
        img = Image.open(resp.raw).convert('RGBA')
        
        # scale the image
        factor = self.max_w / min(img.width, img.height)
        self.img = img.resize((int(img.width * factor), int(img.height * factor)))
        emoji_cache[self.url] = self.img.copy()
    
    def rotate_image(self):
        self.img = self.img.rotate(angle=self.angle, 
                                   expand=True, 
                                   fillcolor=(255,0,0,0))

    def get_image(self):
        return self.img

def sync_tree(storage, sv_id):
    if sv_id not in active_trees:
        return "No tree here."
   
    tree = active_trees[str(sv_id)]
    storage["tree"] = tree.serialize() 
    storage.sync()
    
    return "Done."

def good_ornament(ornament, storage):
    # Don't allow attachments
    if "attachments" in ornament:
        return False
    for emoji in storage["allowed_emoji"]:
        if emoji["discord_id"] in ornament:
            return True
    return False

def ornament_exists(ornament_name, storage):
    for emoji in storage["allowed_emoji"]:
        if emoji["local_name"] == ornament_name:
            return True
    return False

@hook.on_ready()
async def rebuild_trees(bot):
    for server in bot.backend.get_servers():
        if str(server.id) not in SERVERS:
            continue

        storage = bot.server_permissions[server.id].get_plugin_storage("plugins_custom_roddit_christmas.json")
       

        if storage == {}:
            storage["is_active"] = False
            storage["tree"] = {"ornaments": {}, "banner": False, "concluded": False}
            storage["allowed_emoji"] = []
            storage["restricted"] = True
            storage["special_user"] = ""
            storage["unlimited_adders"] = []
            storage["unlimited"] = False
            storage.sync()

        global star_ornament
        star_ornament = Ornament(position=star_position, 
                                 angle=0, 
                                 url=star_URL, 
                                 max_w=100)
        if "tree" not in storage:
            continue
      
        if storage["is_active"]:
            ChristmasTree.deserialize(bot, storage, server)
