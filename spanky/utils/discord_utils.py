import discord

def get_user_by_id(server, uid):
    for u in server.get_users():
        if u.id == uid:
            return u
    return None

def get_role_by_name(server, rname):
    for r in server.get_roles():
        if r.name == rname:
            return r

    return None

def get_role_by_id(server, rid):
    for r in server.get_roles():
        if r.id == rid:
            return r

    return None

def get_channel_by_id(server, cid):
    for c in server.get_channels():
        if c.id == cid:
            return c

    return None

def str_to_id(string):
    return string.strip().replace("@", "").replace("<", "").replace(">", "").replace("!", "").replace("#", "").replace("&", "").replace(":", " ")


def code_block(msg):
    return "```\n%s\n```" % msg


def get_role_names_between(start_role, end_role, server):
    list_roles = {}
    # Get starting and ending positions of listed roles
    for srole in server.get_roles():
        if start_role == srole.name:
            pos_start = srole.position
        if end_role == srole.name:
            pos_end = srole.position

    # List available roles
    for i in server.get_roles():
        if i.position > pos_end and i.position < pos_start:
            list_roles[i.name.lower()] = i

    return list_roles

def get_roles_between(start_role, end_role, server):
    list_roles = []
    # Get starting and ending positions of listed roles
    for srole in server.get_roles():
        if start_role == srole.name:
            pos_start = srole.position
        if end_role == srole.name:
            pos_end = srole.position

    # List available roles
    for i in server.get_roles():
        if i.position > pos_end and i.position < pos_start:
            list_roles.append(i)

    return sorted(list_roles, key=lambda m: m.name)

def user_roles_from_list(user, rlist):
    """
    Given a role list `rlist` return what subset is assigned to the user
    """
    # return list(
    #     set.intersection(
    #         set([i.id for i in user.roles]),
    #         set([i.id for i in rlist]))
    #     )

    common = []
    for urole in user.roles:
        for role in rlist:
            if urole.id == role.id:
                common.append(urole)

    return common

def remove_role_from_list(start_role, end_role, server, event, send_message):
    roles = get_role_names_between(start_role, end_role, server)

    user_roles = []
    for role in event.author.roles:
        if role.name.lower() not in roles:
            user_roles.append(role)

    if len(user_roles) > 0:
        event.author.replace_roles(user_roles)
        send_message("Done!")
    else:
        send_message("You don't have any of the roles.")

def remove_given_role_from_list(start_role, end_role, server, event, send_message, text):
    roles = get_roles_between(start_role, end_role, server)
    text = text.lower()

    for role in roles:
        if role.name.lower() == text:
            event.author.remove_role(role)
            send_message("Done!")
            return

    uroles = set.intersection(set([i.name.lower() for i in event.author.roles]), set([i.name.lower() for i in roles]))
    if text != "":
        send_message("%s is not a role. Try with: %s" % (text, ", ".join("`" + i + "`" for i in uroles)))
    else:
        send_message("You need to specify one of your roles. Try with: %s" % (", ".join("`" + i + "`" for i in uroles)))

def add_role_from_list(start_role, end_role, server, event, send_message, text, max_assignable=1000):
    roles = get_roles_between(start_role, end_role, server)
    text = text.lower().strip()

    uroles = set.intersection(set([i.name.lower() for i in event.author.roles]), set(
        [i.name.lower() for i in roles]))
    if len(uroles) >= max_assignable:
        send_message(
            "You can assign a maximum %d roles. Try removing one of your roles before assigning a new one." % max_assignable)
        return

    if text == "":
        send_message("You need to give me a role name. Try: %s" %
                     (", ".join("`" + i.name.lower() + "`" for i in roles)))
        return

    for role in roles:
        if role.name.lower() == text:
            event.author.add_role(role)
            send_message("Done!")
            return

    send_message("%s is not a role. Try with: %s" % (
        text, ", ".join("`" + i.name.lower() + "`" for i in roles)))

def roles_from_list(start_role, end_role, remove_text, send_message, server, event, bot, text):
    use_slow_mode = False
    text = text.lower()

    bot_roles = bot.get_bot_roles_in_server(server)

    if remove_text:
        list_colors = {remove_text.lower(): None}
    else:
        list_colors = {}
    user_roles = {}

    # Make list of user roles
    for i in event.author.roles:
        user_roles[i.name.lower()] = i

    # Get the highest role that the bot has
    bot_max = 0
    for i in bot_roles:
        if bot_max < i.position:
            bot_max = i.position

    # Decide if the bot can use replace_roles or not
    for i in user_roles:
        if bot_max < user_roles[i].position:
            use_slow_mode = True

    list_colors = dict(**list_colors, **get_role_names_between(start_role, end_role, server))

    # If no role was specified, just print them
    if text == "":
        send_message("Use the command with one of: `%s`" % (", ".join(i for i in sorted(list_colors))))
        return

    split = text.split()
    role = " ".join(split).lower()

    # Check if the requested role exists
    if role not in list_colors:
        send_message("%s is not a role. Use the command with one of: `%s`" % (role, ", ".join(i for i in sorted(list_colors))))
        return

    # If the user wants the role removed
    if role == remove_text:
        for i in list_colors:
            if i in user_roles:
                if use_slow_mode:
                    event.author.remove_role(list_colors[i])
                else:
                    del user_roles[i]
    else:
        # Else the user has requested another role
        # Check if a role from the current list should be removed
        for i in list_colors:
            if i in user_roles and i != role:
                if use_slow_mode:
                    event.author.remove_role(list_colors[i])
                else:
                    del user_roles[i]
        user_roles[role] = list_colors[role]

    # Use slow mode is used whenever the bot has lower rights than the user
    # requesting the roles
    if not use_slow_mode:
        repl_roles = []
        for i in user_roles:
            repl_roles.append(user_roles[i])

        event.author.replace_roles(repl_roles)
        return "Done!"
    else:
        if role != remove_text:
            event.author.add_role(list_colors[role])
        return "Your user rights are higher than what the bot has. Please check if role assignation worked."


def prepare_embed(title, description=None, fields=None, inline_fields=True, image_url=None, footer_txt=None):
    """
    Prepare an embed object
    """
    em = None

    if description:
        em = discord.Embed(title=title, description=description)
    else:
        em = discord.Embed(title=title)

    if fields:
        for el in fields:
            em.add_field(name=el, value=fields[el], inline=inline_fields)

    if image_url:
        em.set_image(url=image_url)

    if footer_txt:
        em.set_footer(text=footer_txt)

    return em