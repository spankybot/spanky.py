from spanky.plugin import hook
from datetime import datetime, timezone

def getUnixTimestamp(snowflake):
    return ((int(snowflake) / 4194304) + 1420070400000) // 1000

dateString = "%Y-%m-%d at %H:%M"

@hook.command(format="mention")
def userinfo(text, str_to_id, reply, server):
    """
    <mention> - gets various data about the mentioned user
    """
    try:
        output = "```"
        id = str_to_id(text)

        if text == "":
            reply("Please mention a user")
            return


        # account creation timestamp
        createTimestamp = datetime.fromtimestamp(getUnixTimestamp(id), tz=timezone.utc)
        output += f"Creation date: {createTimestamp.strftime(dateString)}\n"

        # join timestamp
        rawMember = None
        for member in server.get_users():
            if member.id == id:
                rawMember = member._raw
        if rawMember == None:
            output += f"ID: {id}\n"
            reply(output + "```")
            return

        output += f"Join date: {rawMember.joined_at.strftime(dateString)}\n"
        output += f"Avatar: {rawMember.avatar_url}\n"
        output += f"ID: {id}\n"

        if rawMember.premium_since != None:
            output += f"Boosting since {rawMember.premium_since.strftime(dateString)}\n"

        reply(output + "```")
    except Exception as e:
        print(e)