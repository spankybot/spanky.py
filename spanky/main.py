from SpankyServer.bot import Bot

bot = Bot("discord_py")
bot.loop.run_until_complete(bot.start())

while True:
    import time
    time.sleep(1)
