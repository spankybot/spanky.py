import re

from spanky.plugin import hook

correction_re = re.compile(r"^[sS]/(.*/.*(?:/[igx]{,4})?)\S*$")


@hook.regex(correction_re)
def correction(match, message):
    """
    :type match: re.__Match
    :type conn: cloudbot.client.Client
    :type chan: str
    """
    message("correction")