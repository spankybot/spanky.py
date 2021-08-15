from spanky.hook2 import hook2
import time
from spanky.hook2.event import EventType

hk2 = hook2.Hook(f"plugins_hook2_{int(time.time())}")

print(hk2)

@hk2.command()
def test_hook2(reply):
    reply("COMMAND EXECUTED WITH HOOK2")

from spanky.plugin import hook

@hook.command()
def get_commands(bot):
    print(bot.hook2.children)

@hk2.event(EventType.message_del)
def msg_del_test():
    print("Message deleted")

@hk2.event(EventType.on_ready)
def ready_test(server):
    print("Pula pizda coaiele au inceput razboaiele")

@hk2.event(EventType.on_start)
def start_test():
    print(f"Started beeeyoootch.")

@hk2.event(EventType.on_conn_ready)
def conn_ready_test(): 
    print("Bot ready")
    print("I will suck ur cock")
