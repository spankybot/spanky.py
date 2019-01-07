"""
issafe.py

Check the Google Safe Browsing list to see a website's safety rating.

Created By:
    - Foxlet <http://furcode.tk/>

License:
    GNU General Public License (Version 3)
"""

from urllib.parse import urlparse
import requests
from spanky.plugin import hook

API_SB = "https://sb-ssl.google.com/safebrowsing/api/lookup"


@hook.on_start()
def load_api(bot):
    global dev_key

    dev_key = bot.config.get("api_keys", {}).get("google_dev_key", None)


@hook.command()
def issafe(text):
    """<website> -- Checks the website against Google's Safe Browsing List."""
    if urlparse(text).scheme not in ['https', 'http']:
        return "Check your URL (it should be a complete URI)."

    parsed = requests.get(API_SB, params={"url": text, "client": "cloudbot", "key": dev_key, "pver": "3.1",
                                          "appver": "Spanky.py"})
    parsed.raise_for_status()

    if parsed.status_code == 204:
        condition = "{} is safe.".format(text)
    else:
        condition = "{} is known to contain: {}".format(text, parsed.text)
    return condition
