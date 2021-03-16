import plugins.paged_content as paged
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
        createTimestamp = datetime.fromtimestamp(
            getUnixTimestamp(id), tz=timezone.utc)
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


@hook.command()
async def inrole(text, server, async_send_message):
    """
    [role name] List how many members each role has. Calling it with no role name will list all roles
    """
    role_id = {}
    total_members = 0

    # Map role IDs to usage count
    for user in server.get_users():
        total_members += 1
        for role in user.roles:
            if role.id not in role_id.keys():
                role_id[role.id] = 1
            else:
                role_id[role.id] += 1

    # Map role names to roles for sorting
    alphab_sroles = {}
    for server_role in server.get_roles():
        if server_role.name in ["@everyone", "@here"]:
            continue

        alphab_sroles[server_role.name] = server_role

    # Create string of role names to print
    nice_roles = []

    # If no text was given
    if text == "":
        for srole_name in sorted(alphab_sroles.keys()):
            srole = alphab_sroles[srole_name]

            if srole.id in role_id.keys():
                nice_roles.append("%s: %s" % (srole.name, role_id[srole.id]))
            else:
                nice_roles.append("%s: 0" % (srole.name))
    else:
        for srole_name in sorted(alphab_sroles.keys()):
            if text.lower() not in srole_name.lower():
                continue
            srole = alphab_sroles[srole_name]

            if srole.id in role_id.keys():
                nice_roles.append("%s: %s" % (srole.name, role_id[srole.id]))
            else:
                nice_roles.append("%s: 0" % (srole.name))

    if len(nice_roles) == 0:
        nice_roles = ["Nothing found!"]

    content = paged.element(
        text_list=nice_roles,
        send_func=async_send_message,
        description="Total members: %d" % total_members,
        max_lines=20,
        no_timeout=True)

    await content.get_crt_page()
