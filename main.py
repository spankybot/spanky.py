import sys
from spanky.streamwrap import StreamWrap
# Wrap things early
sys.stdout = StreamWrap(sys.stdout, "stdout")
sys.stderr = StreamWrap(sys.stderr, "stderr")

from spanky.bot import Bot

bot = Bot("nextcord")
bot.loop.run_until_complete(bot.start())

try:
    bot.loop.run_forever()
finally:
    bot.loop.close()
