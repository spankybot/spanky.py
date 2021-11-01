from spanky.bot import Bot

bot = Bot("distributed")
bot.loop.run_until_complete(bot.start())

while True:
    import time

    time.sleep(1)
