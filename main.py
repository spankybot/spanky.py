from spanky.bot import Bot

bot = Bot()

class dummy_msg():
    pass

msg = dummy_msg()
msg.text = ".system"

bot.on_message(msg)

while True:
    import time
    time.sleep(1)
