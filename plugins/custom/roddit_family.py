
# Discord/Plugin things
from spanky.plugin import hook
from spanky.utils import discord_utils as dutils
import discord
from spanky.plugin.permissions import Permission

# Image/Family tree stuff
from PIL import Image
from graphviz import Digraph
import io

# Type stuff (I'm experimenting with this, it's my first time)
from typing import Dict, List, Optional, Set
from enum import IntEnum
import spanky.inputs.discord_py as dpy

# Other util stuff
import secrets

SERVER_IDS = [
    "648937029433950218", # Dev Server
    "287285563118190592" # r/ro
]
ELEVATED_PERMS = [Permission.admin, Permission.bot_owner]
PLUGIN_DATA_NAME = "plugins_custom_roddit_family.json"
PLUGIN_MAINTAINER = "195202549647671297" # CNC#9999

server_trees = {}

RelativeDict = Dict[int, Set['Person']]

node_attributes = [('shape', 'box')]
edge_attributes = [('dir', 'none')]
graph_attributes = []

no_mentions = discord.AllowedMentions.none()

class RelativeException(Exception):
    def __init__(self, p1, p2):
        self.p1 = p1
        self.p2 = p2
        self.err = f"{p1.name} e o rudă a lui {p2.name}"
        super().__init__(self.err)

class OfferType(IntEnum):
    MARRY = 1
    ADOPT = 2
    CHOICE = 3

class PendingOffer:
    """
    oid: request ID type
    tp: OfferType the type
    fr: str, User ID for the person requesting
    to: str, User ID for the person being asked
    """

    def __init__(self, oid: str, tp: OfferType, fr: str, to: str):
        self.id = oid
        self.tp = tp
        self.fr = fr
        self.to = to

    def serialize(self):
        rez = {}
        rez["id"] = self.id
        rez["type"] = self.tp
        rez["from"] = self.fr
        rez["to"] = self.to
        return rez

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f"Request {self.id}: from <@{self.fr}> to <@{self.to}>. Type {repr(self.tp)}"

    @staticmethod
    def create(tp: OfferType, fr: str, to: str):
        oid = secrets.token_urlsafe(6)
        return PendingOffer(oid, tp, fr, to)

    @staticmethod
    def deserialize(serialized):
        return PendingOffer(serialized["id"], OfferType(serialized["type"]), serialized["from"], serialized["to"])

class Person:
    def __init__(self, uid: str, name: str, spouse="", children=[], parents=[]):
        self.id = uid
        self.name = name
        self.tree: 'ServerTree' = None
        
        self.raw_spouse = spouse
        self.raw_children = children
        self.raw_parents = parents
        self.spouse: Optional['Person'] = None
        self.children: List['Person'] = []
        self.parents: List['Person'] = []
    
    def __repr__(self):
        return self.__str__()
    def __str__(self):
        return f"Person[id: {self.id}, name: {self.name}]"
    def __eq__(self, other):
        if isinstance(other, Person):
            return self.id == other.id
        if isinstance(other, str):
            return self.id == other
        return False
    def __hash__(self):
        return hash(self.id)

    # load_info loads all other Persons from the tree
    # It also gets the tree for further modifications
    def load_info(self, tree):
        self.tree = tree
        if self.raw_spouse != "":
            try:
                self.spouse = tree.get_person(self.raw_spouse)
            except:
                pass
        for child in self.raw_children:
            try:
                p = tree.get_person(child)
                if p:
                    self.children.append(p)
            except:
                pass

        for parent in self.raw_parents:
            try:
                p = tree.get_person(parent)
                if p:
                    self.parents.append(p)
            except:
                pass

    # For someone to marry another user
    def marry(self, user_id):
        if self.is_relative(user_id):
            raise RelativeException(self, self.tree.get_person(user_id))
        offer = PendingOffer.create(OfferType.MARRY, self.id, user_id)
        self.tree.add_offer(offer)
        print("Marriage action made from %s with %s" % (self.id, user_id))
        return offer
    
    # For someone to adopt another user
    def adopt(self, user_id):
        if self.is_relative(user_id):
            raise RelativeException(self, self.tree.get_person(user_id))
        offer = PendingOffer.create(OfferType.ADOPT, self.id, user_id)
        self.tree.add_offer(offer)
        print("Adopt action made from %s with %s" % (self.id, user_id))
        return offer
    
    # complete_marriage is called by the tree to update the spouse
    def complete_marriage(self, spouse: 'Person'):
        self.spouse = spouse
        # merge existing children
        self.children = list(set(self.children + self.spouse.children))
        # Very infuriating bug
        for child in self.children:
            child.parents = [self, spouse]
        self.spouse.children = self.children.copy()
        self.sync()
    
    def complete_adoption(self, relative: 'Person', tp: str):
        if tp == "child": # relative becomes a child
            self.children.append(relative)
            if self.spouse:
                self.spouse.children.append(relative)
        else:
            self.parents.append(relative)
            if relative.spouse:
                self.parents.append(relative.spouse)
        self.sync()

    # For someone to divorce married user
    def divorce(self, from_spouse=False):
        if not from_spouse:
            self.spouse.divorce(from_spouse=True)
        self.spouse = None
        self.sync()
    
    # get_all_relatives gets all the relatives from a person in no particular order
    # this assumes that the family graph is acyclic
    def get_all_relatives(self) -> List['Person']:
        out = []
        for _, v in self.get_relative_levels().items():
            for person in v:
                out.append(person)
        return out
    
    def get_relative_levels(self) -> RelativeDict:
        levels: RelativeDict = {}
        self.fill_relative_dict(levels, 0, self.id)
        return levels

    def fill_relative_dict(self, levels: RelativeDict, curr_level: int, asker: str):
        if curr_level not in levels:
            levels[curr_level] = set()
        
        levels[curr_level].add(self)
        
        if self.spouse and self.spouse.id != asker and self.spouse not in levels[curr_level]:
            self.spouse.fill_relative_dict(levels, curr_level, self.id)
        
        for p in self.parents:
            if p.id != asker and (curr_level - 1 not in levels or p not in levels[curr_level - 1]):
                p.fill_relative_dict(levels, curr_level - 1, self.id)
        
        for c in self.children:
            if c.id != asker and (curr_level + 1 not in levels or c not in levels[curr_level + 1]):
                c.fill_relative_dict(levels, curr_level + 1, self.id)

    # This should be used so that family trees make sense
    def is_relative(self, user_id: str):
        for relative in self.get_all_relatives():
            if relative.id == user_id:
                return True
        return False

    # For parents to disown their child
    def disown(self, child_id: str) -> bool:
        if child_id not in [c.id for c in self.children]:
            return False
        for child in self.children:
            if child.id == child_id:
                child.delete_parent(self.id)
                break
        self.tree.get_person(child_id).parents = []
        self.delete_kid(child_id)
        if self.spouse:
            self.spouse.delete_kid(child_id)
        return True


    def get_marriage_cross(self):
        if not self.spouse:
            return ''
        uid = self.id
        sid = self.spouse.id
        if int(uid) > int(sid):
            uid, sid = sid, uid
        return f"{uid}x{sid}"

    def family_tree(self) -> Image.Image:
        ranks = self.get_relative_levels()
        g = Digraph(name='family', 
                    format='png',
                    edge_attr=edge_attributes,
                    graph_attr=graph_attributes,
                    node_attr=node_attributes,
                    strict=True)
        levels = self.get_relative_levels()

        lvl_ids = sorted(list(levels.keys()))
        
        for level in lvl_ids:
            people = levels[level]

            added_already = []

            cross_set = set()
            with g.subgraph() as s:
                s.attr(rank='same', rankdir='LR')
                for person in people:
                    if person.id in added_already:
                        continue
                    added_already.append(person.id)
                    # draw the person
                    if person.id == self.id:
                        s.node(person.id, label=person.name, color='blue')
                    else:
                        s.node(person.id, label=person.name)
                    
                    if not person.married:
                        for child in person.children:
                            g.edge(person.id, child.id)
                        continue

                    # draw the spouse
                    spouse = person.spouse
                    if spouse.id == self.id:
                        s.node(spouse.id, label=spouse.name, color='blue')
                    else:
                        s.node(spouse.id, label=spouse.name)
                    added_already.append(spouse.id)

                    cross = person.get_marriage_cross()
                    if cross not in cross_set:
                        cross_set.add(cross)
                        s.node(cross, label="", shape="point", width="0.001", height="0.001")
                        if person.id < spouse.id:
                            g.edge(person.id, cross)
                            g.edge(cross, spouse.id)
                        else:
                            g.edge(spouse.id, cross)
                            g.edge(cross, person.id)
                        for child in person.children:
                            g.edge(cross, child.id)
        out = g.pipe(format="png")
        return Image.open(io.BytesIO(out))

    def delete_kid(self, child_id: str):
        self.children = [child for child in self.children if child.id != child_id]
        self.sync()
    
    def delete_parent(self, parent_id: str):
        self.parents = [parent for parent in self.parents if parent.id != parent_id]
        self.sync()

    # For children to abandon their parents
    def cut_parent_ties(self):
        for parent in self.parents:
            parent.delete_kid(self.id)
        self.parents = []
        self.sync()
        pass

    @property
    def adopted(self):
        return len(self.parents) > 0

    @property
    def has_kids(self):
        return len(self.children) > 0
    
    @property
    def married(self):
        return self.spouse is not None
    
    @property
    def alone(self):
        return not (self.married or self.adopted or self.has_kids)

    # If the current person has a marriage request to someone, it returns the PendingOffer, else it returns None
    @property
    def marry_request(self):
        for offer in self.tree.offer_outbox(self.id):
            if offer.tp is OfferType.MARRY:
                return True
        return False
    
    @property
    def adopt_request(self):
        for offer in self.tree.offer_outbox(self.id):
            if offer.tp is OfferType.ADOPT:
                return True
        return False
    
    @property
    def divorced_child(self):
        for offer in self.tree.offer_inbox(self.id):
            if offer.tp is OfferType.CHOICE:
                return True
        return False

    def sync(self):
        self.tree.sync()
    
    ##### Storage stuff

    def serialize(self):
        ret = {
            "spouse": "", 
            "children": [], 
            "parents": []
        }
        
        if self.spouse:
            ret["spouse"] = self.spouse.id

        for child in self.children:
            ret["children"].append(child.id)

        for parent in self.parents:
            ret["parents"].append(parent.id)
        return ret

    @staticmethod
    def deserialize(serialized, uid, name):
        return Person(uid, name, serialized["spouse"], serialized["children"], serialized["parents"])

class ServerTree:
    """ServerTree holds a "graph" of relationships in the server"""

    def __init__(self, storage, server, people: Dict[str, Person], offers: List[PendingOffer]):
        self.storage = storage
        self.server = server
        self.people = people
        self.pending_offers = offers
        
        self.fully_load_people()
    
    def fully_load_people(self):
        for id in self.people.keys():
            self.people[id].load_info(self)
        self.sync()
    
    ##### Offer stuff

    def get_offer(self, id) -> Optional[PendingOffer]:
        for offer in self.pending_offers:
            if offer.id == id:
                return offer
        return None

    def add_offer(self, offer: PendingOffer):
        self.pending_offers.append(offer)
        self.sync()

    def remove_offer(self, offer: PendingOffer):
        self.pending_offers.remove(offer)
        self.sync()


    def outbox_by_event_type(self, user_id: str, ot: OfferType) -> List[PendingOffer]:
        offers = []
        for offer in self.offer_outbox(user_id):
            if offer.tp == ot:
                offers.append(offer)
        return offers

    def clear_with_event_type(self, user_id: str, ot: OfferType):
        self.pending_offers = [offer for offer in self.pending_offers if not (offer.fr == user_id and offer.tp == ot)]
        self.sync()

    # offer_inbox returns a list of offers
    def offer_inbox(self, user_id: str) -> List[PendingOffer]:
        offers = []
        for offer in self.pending_offers:
            if offer.to == user_id:
                offers.append(offer)
        return offers

    def offer_outbox(self, user_id: str) -> List[PendingOffer]:
        offers = []
        for offer in self.pending_offers:
            if offer.fr == user_id:
                offers.append(offer)
        return offers

    # This does stuff it should not do, but fuck it, it's already getting pretty late and I need to ship this
    # It returns the message to be sent in the channel
    def start_divorce_event(self, parent: Person) -> str:
        ch_ids = []
        for ch in parent.children:
            self.add_offer(PendingOffer.create(OfferType.CHOICE, ch.id, parent.id))
            self.add_offer(PendingOffer.create(OfferType.CHOICE, ch.id, parent.spouse.id))
            ch_ids.append(ch.id)
        # Disown all children
        for id in ch_ids:
            parent.disown(id)
        # Generate message
        msg = f"Ai divorțat de <@{parent.spouse.id}>. Îmi pare rău, erați foarte frumoși împreună.\n"
        if len(ch_ids) == 0:
            pass
        elif len(ch_ids) == 1:
            msg += f"<@{ch_ids[0]}>, poți să alegi cu ce părinte ai vrea să rămâi. Rulează `.choose_parent <părinte>` pentru a alege pe cineva, iar `.leave_parents` dacă nu vrei să fii asociat cu părinții tăi."
        else:
            mentions = ' '.join([f"<@{id}>" for id in ch_ids])
            msg += f"{mentions}, puteți să alegeți cu ce părinte vreți să rămâneți. Rulați `.choose_parent <părinte>` pentru a alege pe cineva, iar `.leave_parents` dacă nu vreți să fiți asociați cu părinții voștri."
        parent.divorce()
        self.sync()
        return msg

    ##### Person Stuff
    
    def get_person(self, uid: str) -> Person:
        person = self.people.get(uid)
        if not person:
            user = self.server.get_user(uid)
            if not user:
                raise ValueError("invalid user id")
            return self.create_person_from_user(user)
        return self.people[uid]
    
    def get_member(self, person: Person) -> dpy.User:
        return self.server.get_user(person.id)

    def create_person_from_user(self, user) -> Person:
        return self.create_person(user.id, user.name)

    def create_person(self, uid: str, name: str) -> Person:
        p = Person(uid, name)
        p.load_info(self)
        self.add_person(p)
        return p

    def add_person(self, person: Person):
        self.people[person.id] = person
        self.sync()

    # Storage stuff

    def serialize(self):
        offers = []
        for offer in self.pending_offers:
            offers.append(offer.serialize())
        
        people = {}
        for uid, person in self.people.items():
            people[uid] = person.serialize()

        return {"offers": offers, "people": people}

    def sync(self):
        data = self.serialize()
        self.storage["server_tree"] = data
        self.storage.sync()

    @staticmethod
    def deserialize(bot, storage, server) -> 'ServerTree':
        serialized = storage["server_tree"]
        raw_people = serialized["people"]
        raw_offers = serialized["offers"]
        people = {}
        offers = []
        for uid, person in raw_people.items():
            user = server.get_user(uid)
            if user is None:
                continue
            people[uid] = Person.deserialize(person, uid, user.name)
        
        for offer in raw_offers:
            offer["type"] = OfferType(offer["type"])
            off = PendingOffer.deserialize(offer)
            if off.to not in people or off.fr not in people:
                continue
            offers.append(off)

        tree = ServerTree(storage, server, people, offers)
        server_trees[str(server.id)] = tree        
        return tree

def get_server_tree(event) -> ServerTree:
    return server_trees[str(event.server.id)]

@hook.command(server_id=SERVER_IDS, format="user")
def marry(event, text):
    """<user> - Inițiază o cerere în căsătorie cu persoana menționată"""
    tree = get_server_tree(event)
    p = tree.get_person(event.author.id)
    text = dutils.str_to_id(text)
    if text == "":
        return "Trebuie să specifici pe cineva"

    user = event.server.get_user(text)
    if not user:
        return "Persoană invalidă."
    
    if p.married:
        return "Ești deja căsătorit!"
    if user.id == event.author.id:
        return "Oricât de mult ai vrea, nu te poți căsători cu tine :("
    if p.marry_request:
        return "Ai deja o cerere de căsătorie expediată! Rulează .revoke_marry_request ca să o anulezi"
    spouse = tree.get_person(user.id)
    if spouse.married:
        return "Persoana e deja luată, nu ai ce să-i faci."
    if spouse.id in [ch.id for ch in p.children]:
        return "Nu-ți poți căsători copiii."
    if spouse.id in [pr.id for pr in p.parents]:
        return "Nu-ți poți căsători părinții."
    if p.is_relative(user.id):
        return "Nu poți căsători o rudă."


    req = p.marry(spouse.id)  
    
    user.send_pm(f"""Ai primit o cerere de căsătorie de la {event.author.name}
Răspunde cu următoarea comandă pentru a accepta cererea:
.accept_marry {req.id}
Dacă vrei să refuzi această cerere, răspunde cu următoarea comandă:
.deny_marry {req.id}""")

    return "Ai trimis cerere de căsătorie lui %s." % user.name

@hook.command(can_pm=True, format="id")
def accept_marry(bot, text, event, reply):
    """<id> - Acceptă o ofertă de căsătorie."""
    if text == "":
        return "Trebuie specificat ID-ul cererii!"

    for server in bot.backend.get_servers():
        if server.id not in SERVER_IDS:
            continue
        tree: ServerTree = server_trees[str(server.id)]
        offer = tree.get_offer(text)
        print(tree.pending_offers)
        if not offer: 
            continue
        if offer.to != event.author.id:
            return "Cererea nu îți este destinată ție!"
        if offer.tp != OfferType.MARRY:
            return "Asta nu-i cerere de căsătorie!"
        p1 = tree.get_person(event.author.id)
        p2 = tree.get_person(offer.fr)
        # check if person is relative, again
        if p1.is_relative(offer.fr):
            tree.remove_offer(offer)
            return "Din păcate, ați devenit rude, deci nu mai puteți face nimic"
        p1.complete_marriage(p2)
        p2.complete_marriage(p1)
        tree.remove_offer(offer)


        user = server.get_user(offer.fr)

        user.send_pm(f"{event.author.name} ți-a acceptat cererea de căsătorie. Casă de piatră!") 
        return "Casă de piatră!"

    return "ID invalid"

@hook.command(can_pm=True, format="id")
def deny_marry(bot, text, event):
    """<id> - Refuză o ofertă de căsătorie"""
    for server in bot.backend.get_servers():
        if server.id not in SERVER_IDS:
            continue

        tree = server_trees[str(server.id)]
        offer = tree.get_offer(text)
        if not offer: 
            continue
        if offer.to != event.author.id:
            return "Cererea nu îți este destinată ție!"
        if offer.tp != OfferType.MARRY:
            return "Asta nu-i cerere de căsătorie!"
        
        user = server.get_user(offer.fr)
        user.send_pm(f"{event.author.name} ți-a refuzat cererea de căsătorie. Mai mult noroc data viitoare!") 
        return "I-am transmis veștile."
    
    return "ID invalid"

@hook.command(server_id=SERVER_IDS, format="user")
def adopt(event, text):
    """<user> - Inițiază o cerere de adopție cu user-ul menționat"""
    tree = get_server_tree(event)
    p = tree.get_person(event.author.id)
    text = dutils.str_to_id(text)

    if p.adopt_request:
        return "Poți adopta o singură persoană în orice moment! Rulează .revoke_adopt_request pentru a anula cererea"
    
    if text == "":
        return "Trebuie să specifici pe cineva pe care să adoptezi"
    user = event.server.get_user(text)

    if not user:
        return "Persoană invalidă."
    if user.id == event.author.id:
        return "Oricât de mult ai vrea, nu te poți adopta pe tine însăți. :("
    if p.spouse and p.spouse.id == user.id:
        return "Nu îți poți adopta consortul."
    if user.id in [c.id for c in p.children]:
        return "Ai adoptat deja acea persoană."
    if user.id in [p.id for p in p.parents]:
        return "Nu îți poți adopta părinții."
    if p.is_relative(user.id):
        return "Nu poți adopta rudele."
    child = tree.get_person(user.id)
    if child.adopted:
        return "Persoana este deja adoptată"

    req = p.adopt(child.id)  
    print(req)

    user.send_pm(f"""Ai primit o cerere de adopție de la {event.author.name}
Răspunde cu următoarea comandă pentru a accepta cererea:
.accept_adoption {req.id}
Dacă vrei să refuzi această cerere, răspunde cu următoarea comandă:
.deny_adoption {req.id}""")

    return "Ai trimis cerere de adopție lui %s." % user.name

@hook.command(can_pm=True, format="id")
def accept_adoption(bot, text, event, reply, send_message):
    """<id> - Acceptă o ofertă de adopție"""
    for server in bot.backend.get_servers():
        if server.id not in SERVER_IDS:
            continue
        tree: ServerTree = server_trees[str(server.id)]
        offer = tree.get_offer(text)
        print(tree.pending_offers)
        if not offer: 
            continue
        if offer.to != event.author.id:
            return "Cererea nu îți este destinată ție!"
        if offer.tp != OfferType.ADOPT:
            return "Asta nu-i cerere de adopție!"
        
        p1 = tree.get_person(offer.to)
        p2 = tree.get_person(offer.fr)
        # check if person is relative, again
        if p1.is_relative(offer.fr):
            tree.remove_offer(offer)
            return "Din păcate, ați devenit rude, deci nu mai puteți face nimic"
        p2.complete_adoption(p1, "child")
        p1.complete_adoption(p2, "parent")
        tree.clear_with_event_type(event.author.id, OfferType.CHOICE)
        tree.remove_offer(offer)

        user = server.get_user(offer.fr)
        user.send_pm(f"{event.author.name} ți-a acceptat cererea de adopție. Nu pot oferi scutecele.") 
        return "Salută-ți părinții din partea mea!"

    return "ID invalid"

@hook.command(can_pm=True, format="id")
def deny_adoption(bot, text, event):
    """<id> - Refuză o ofertă de adopție"""
    for server in bot.backend.get_servers():
        if server.id not in SERVER_IDS:
            continue

        tree = server_trees[str(server.id)]
        offer = tree.get_offer(text)
        if not offer: 
            continue
        if offer.to != event.author.id:
            return "Cererea nu îți este destinată ție!"
        if offer.tp != OfferType.ADOPT:
            return "Asta nu-i cerere de adopție!"
        
        user = server.get_user(offer.fr)
        user.send_pm(f"{server.get_user(offer.to).name} ți-a refuzat cererea de adopție. Încă n-a crescut suficient :(") 
        return "I-am transmis veștile."
    
    return "ID invalid"

@hook.command(server_id=SERVER_IDS)
def revoke_marry_request(text, event):
    """Dacă te-ai răzgândit și nu vrei să te căsătorești."""
    tree = get_server_tree(event)
    # This assumes there's only one outbox marry requests (which should be what's true)
    for offer in tree.offer_outbox(event.author.id):
        if offer.tp != OfferType.MARRY:
            continue
        u = event.server.get_user(offer.to)
        u1 = event.server.get_user(offer.fr)
        u.send_pm(f"Oferta de căsătorie de la {u1.name} a fost anulată.") 
        tree.remove_offer(offer)
        return "Done"

    return "Nu ai trimis nicio cerere de căsătorie."

@hook.command(server_id=SERVER_IDS)
def revoke_adopt_request(text, event):
    """Dacă te-ai răzgândit și nu vrei să adoptezi pe cineva."""
    tree = get_server_tree(event)
    for offer in tree.offer_outbox(event.author.id):
        if offer.tp != OfferType.ADOPT:
            continue
        u = event.server.get_user(offer.to)
        u1 = event.server.get_user(offer.fr)
        u.send_pm(f"Oferta de adopție de la {u1.name} a fost anulată.") 
        tree.remove_offer(offer)
        return "Done"

    return "Nu ai trimis nicio cerere de adopție către acea persoană."

@hook.command(server_id=SERVER_IDS)
def divorce(event):
    """Divorțează cu partenerul tău."""
    p = get_server_tree(event).get_person(event.author.id)
    if not p.married:
        return "Nu ești căsătorit!"
    old_spouse = p.spouse
    user = get_server_tree(event).get_member(p.spouse)
    user.send_pm("Partenerul tău, %s, a decis să divorțeze cu tine. Nu te merita, crede-mă" % event.author.name)
    return get_server_tree(event).start_divorce_event(p)

@hook.command(server_id=SERVER_IDS, format="parent")
def choose_parent(event, text):
    """<părinte> - Alege părintele cu care vrei să rămâi după divorț."""
    text = dutils.str_to_id(text)
    u = event.server.get_user(text)
    if not u:
        return "Nu ai menționat utilizator!"
    tree = get_server_tree(event)
    p = tree.get_person(event.author.id)
    if p.adopted:
        return "Ești deja adoptat, nu poți alege pe cineva!"

    offers = tree.outbox_by_event_type(event.author.id, OfferType.CHOICE)
    if len(offers) == 0:
        return
    if text not in [offer.to for offer in offers]:
        return "Persoana nu e părintele tău!"
    p1 = tree.get_person(text)
    p1.complete_adoption(p, "child")
    p.complete_adoption(p1, "parent")
    tree.clear_with_event_type(event.author.id, OfferType.CHOICE)
    return "Ți-ai ales un părinte, sper că veți continua fericiți"

@hook.command(server_id=SERVER_IDS)
def leave_parents(event):
    """Nu alege niciun părinte cu care să rămâi. Nu vei mai putea alege un părinte după."""
    tree = get_server_tree(event)
    if len(tree.outbox_by_event_type(event.author.id)) == 0:
        return
    tree.clear_with_event_type(event.author.id, EventType.CHOICE)
    return "Ți-ai lăsat părinții divorțați în urmă"

@hook.command(server_id=SERVER_IDS)
def disown(text, event):
    """<user> - Dezmoștenește unul din copii"""
    tree = get_server_tree(event)
    text = dutils.str_to_id(text)
    if text == "":
        return "Trebuie să specifici pe cineva să dezmoștenești"
    p = tree.get_person(event.author.id)
    if not p.disown(text):
        return "Persoană invalidă"
    c = event.server.get_user(text)
    c.send_pm("Părinții tăi au decis că nu meriți să fii copilul lor. Ești pe cont propriu. :'(")
    if p.spouse:
        user = tree.get_member(p.spouse)
        user.send_pm("Partenerul tău a decis să %s nu merită să fie copilul vostru." % c.name)
    return "Gata, ai mai scăpat de o grijă"


@hook.command(server_id=SERVER_IDS)
def run_away(event):
    """Fugi de acasă. Sunt eliminate toate legăturile cu părinții tăi."""
    p = get_server_tree(event).get_person(event.author.id)
    if not p.adopted:
        return "Nu ești adoptat!"
    old_parents = p.parents
    for parent in old_parents:
        user = get_server_tree(event).get_member(parent)
        user.send_pm("Copilul tău, %s, a fugit de acasă. Trebuia să-l tratezi mai bine :(" % event.author.name)
    p.cut_parent_ties()
    return "Ai fugit de acasă"

###########################################################
# INFORMATIVE STUFF #######################################
###########################################################

@hook.command(server_id=SERVER_IDS)
def offer_inbox(event, reply):
    """Afișează toate cererile disponibile pe care le-ai primit."""
    offers = get_server_tree(event).offer_inbox(event.author.id)
    if len(offers) == 0:
        return "Nu-i nimic"
    ret = ""
    for offer in offers:
        if offer.tp == OfferType.MARRY:
            ret += "Cerere de căsătorie de la <@%s>" % offer.fr
        if offer.tp == OfferType.ADOPT:
            ret += "Ofertă de adopție de la <@%s>" % offer.fr
        if offer.tp == OfferType.CHOICE:
            ret += "Opțiune de ales părinte: <@%s>" % offer.fr
    reply(ret, allowed_mentions=no_mentions)

@hook.command(server_id=SERVER_IDS)
def offer_outbox(event, reply):
    """Afișează toate cererile disponibile pe care le-ai trimis."""
    offers = get_server_tree(event).offer_outbox(event.author.id)
    if len(offers) == 0:
        return "Nu-i nimic"
    ret = ""
    for offer in offers:
        if offer.tp == OfferType.MARRY:
            ret += "Cerere de căsătorie către <@%s>" % offer.to
        if offer.tp == OfferType.ADOPT:
            ret += "Ofertă de adopție către <@%s>" % offer.to
        if offer.tp == OfferType.CHOICE:
            ret += "Opțiune de ales părinte către <@%s>" % offer.to
    reply(ret, allowed_mentions=no_mentions)


@hook.command(server_id=SERVER_IDS)
def bug_report(text):
    """<text> - raportează un bug către cel care se ocupă cu această funcționalitate a botului."""
    return f"<@{PLUGIN_MAINTAINER}>"


@hook.command(server_id=SERVER_IDS)
def family_info():
    """Informații generale despre comenzile legate de familie"""
    return """
Bine ați venit la sistemul de familii r/Romania!
Aici, aveți ocazia să stabiliți numeroase relații ficționale cu alți membri ai server-ului: puteți să vă căsătoriți, să adoptați, să fiți adoptat, să divorțați, etc.

Puteți începe căsătorind pe cineva cu `.marry`. Botul va trimite în DM-uri un cod unic pentru ofertă. Potențialul partener poate să accepte sau să refuze oferta! 
Asemănător, puteți adopta pe cineva cu `.adopt`, de menționat că poți încerca să adopți o singură persoană într-un moment.

Odată ce stabiliți câteva relații, puteți rula `.family_tree` pentru a vedea arborele vostru genealogic. Puteți vedea și arborele altuia menționându-l când executați comanda.

Comanda `.family_support` vă oferă o listă întreagă de comenzi rulabile, bazat pe relațiile stabilite. `.family_support full` le afișează pe toate indiferent de relații, dacă sunteți curioși 😄

Când divorțezi, copiii primesc șansa să rămână cu un părinte, nu trebuie readoptați! Dacă ei sunt adoptați de altcineva între timp, nu se mai pot întoarce la voi.


Sistemul nu este perfect, dacă găsiți un bug nu ezitați să rulați comanda `.bug_report` cu problema, iar autorul sistemului va încerca să o rezolve cât mai rapid.
Spor!
""".strip()

@hook.command(server_id=SERVER_IDS)
def family_support(event, text):
    """Afișează toate comenzile pe care le poate face cineva. Lista se poate schimba după mulți factori. `.family_support full` dezactivează dinamicitatea """
    p = get_server_tree(event).get_person(event.author.id)
    ret = "Comenzi disponibile:\n```\n"
    show_full = text == "full"
    funcs = [family_info, family_tree]
    empty_line = gen_func("")
    
    funcs.append(empty_line)
    if p.married or show_full:
        funcs.append(divorce)
    
    if not p.married or show_full:
        funcs.append(marry)
    if not p.adopt_request or show_full:
        funcs.append(adopt)
    
    if p.marry_request or show_full:
        funcs.append(revoke_marry_request)
    if p.adopt_request or show_full:
        funcs.append(revoke_adopt_request)

    if len(p.children) > 0 or show_full:
        funcs.append(disown)

    if p.divorced_child or show_full:
        funcs.append(empty_line)
        funcs.extend([choose_parent, leave_parents])
        funcs.append(empty_line)

    if p.adopted or show_full:
        funcs.append(run_away)

    funcs.extend([empty_line, offer_inbox, offer_outbox, empty_line])

    funcs.extend([bug_report, family_support])

    if event.author.bot_owner:
         funcs.extend([gen_func("\n### Comenzi nedestinate publicului"), raw_relationships, get_person_info, get_requests, clear_requests, clear_relationships])
         
    for func in funcs:
        if "__custom__" in dir(func):
            ret += "%s\n" % func.__doc__
            continue
        name = func.__name__
        doc = func.__doc__
        if not doc:
            doc = "#TODO - documentație"
        ret += ".%s - %s\n" % (name, doc.strip())
    return ret + "```"

# Generates a function made to fit nicely in the help command
def gen_func(doc):
    def tmp():
        pass
    tmp.__doc__ = doc
    tmp.__custom__ = True
    return tmp

@hook.command(server_id=SERVER_IDS)
def family_tree(event, text):
    """<user> - Afișează arborele genealogic al unei persoane. Dacă nu este menționat cineva, va afișa arborele tău genealogic"""
    pid = event.author.id
    text = dutils.str_to_id(text)
    if text != "":
        pid = text
    try:
        user = get_server_tree(event).get_person(pid)
    except:
        return "Persoană invalidă"
    if user.alone:
        return "Nu-i nicio familie de arătat. :("
    try:
        return dutils.pil_to_dfile(user.family_tree()) 
    except:
        import traceback
        bio = io.StringIO()
        traceback.print_exc(file=bio)
        return "```"+bio.getvalue()+"```"

###########################################################
# MAINTAINING STUFF #######################################
###########################################################

@hook.command(server_id=SERVER_IDS, permissions=Permission.bot_owner)
def raw_relationships(event, text, async_send_message):
    """<user> - Afișează toate rudele unei persoane, pe câte un nivel al arborelui genealogic"""
    pid = event.author.id
    text = dutils.str_to_id(text)
    if text != "":
        pid = text
    try:
        p = get_server_tree(event).get_person(pid)
    except:
        return "Persoană invalidă"
    return str(p.get_relative_levels())

@hook.command(server_id=SERVER_IDS, permissions=Permission.bot_owner)
def get_person_info(event, reply, text):
    """<user> - Afișează informații despre persoana respectivă"""
    pid = event.author.id
    text = dutils.str_to_id(text)
    if text != "":
        pid = text
    msg = ""
    try:
        p = get_server_tree(event).get_person(pid)
    except:
        return "Persoană invalidă"
    msg += f"id: {p.id}\n"
    msg += f"name: {p.name}\n"
    msg += f"married? {p.married}\n"
    msg += f"marry request? {p.marry_request}\n"
    if p.spouse:
        msg += f"married to: <@{p.spouse.id}>\n"
    if p.children:
        msg += f"children: {','.join([f'<@{c.id}>' for c in p.children])}\n"
    if p.parents:
        msg += f"parents: {','.join([f'<@{pr.id}>' for pr in p.parents])}\n"
    reply(msg, allowed_mentions=no_mentions)

@hook.command(server_id=SERVER_IDS, permissions=Permission.bot_owner)
def get_requests(event, reply):
    """Afișează toate cererile"""
    msg = ""
    for i in get_server_tree(event).pending_offers:
        msg += str(i) + "\n"
    reply(msg, allowed_mentions=no_mentions)

@hook.command(server_id=SERVER_IDS, permissions=Permission.bot_owner)
def clear_requests(event):
    """Golește toate cererile. Nu este indicat să rulezi comanda în niciun caz"""
    tree = get_server_tree(event)
    tree.pending_offers = [] 
    tree.sync()
    return "Done."

@hook.command(server_id=SERVER_IDS, permissions=Permission.bot_owner)
def clear_relationships(event):
    """Golește toate relațiile. Dacă se strică prea rău arborele"""
    try:
        tree = get_server_tree(event)
        tree.people = {}
        tree.sync()
    except:
        import traceback
        bio = io.StringIO()
        traceback.print_exc(file=bio)
        return "```"+bio.getvalue()+"```"
    return "Done."

#############################################
# INITIALIZING STUFF ########################
#############################################

@hook.on_ready()
def load_from_storage(bot):
    for server in bot.backend.get_servers():
        if str(server.id) not in SERVER_IDS:
            continue

        storage = bot.server_permissions[server.id].get_plugin_storage(PLUGIN_DATA_NAME)

        if storage == {}:
            # Set initial stuff
            storage["server_tree"] = {"offers": [], "people": {}}
            storage.sync()
        
        ServerTree.deserialize(bot, storage, server)
