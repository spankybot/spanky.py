from spanky.bot import Bot

bot = Bot("console")

class dummy_msg():
    pass

msg = dummy_msg()
msg.text = ".system"
msg.channel = "#main"
msg.author = "yo"

bot.on_message(msg)

msg.text = ".test2"
bot.on_message(msg)

while True:
    import time
    bot.on_periodic()
    time.sleep(1)
