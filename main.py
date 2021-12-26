from spanky.bot import Bot
import asyncio

bot = Bot("nextcord")
bot.loop.run_until_complete(bot.start())

try:
    bot.loop.run_forever()
finally:
    bot.loop.close()
