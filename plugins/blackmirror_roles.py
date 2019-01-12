from spanky.plugin import hook

BM_ID = "349583192921079808"

no_role = "no role".lower()

@hook.command(server_id=BM_ID)
def charlie(send_message, server, event, bot, text):
    use_slow_mode = False

    bot_roles = bot.get_bot_roles_in_server(server)

    list_colors = {no_role: None}
    user_roles = {}
    for i in event.author.roles:
        user_roles[i.name.lower()] = i

    # Decide if the bot can use replace_roles or not
    bot_max = 0
    for i in bot_roles:
        if bot_max < i.position:
            bot_max = i.position

    for i in user_roles:
        if bot_max < user_roles[i].position:
            use_slow_mode = True

    for srole in server.get_roles():
        if "START BOT ROLES" in srole.name:
            pos_start = srole.position
        if "END BOT ROLES" in srole.name:
            pos_end = srole.position

    for i in server.get_roles():
        if i.position > pos_end and i.position < pos_start:
            list_colors[i.name.lower()] = i

    if text == "":
        send_message("Available roles: `%s`" % (", ".join(i for i in sorted(list_colors))))
        return

    split = text.split()
    role = " ".join(split).lower()

    if role not in list_colors:
        send_message("%s is not a role. Available roles: `%s`" % (role, ", ".join(i for i in sorted(list_colors))))
        return

    if role == no_role:
        for i in list_colors:
            if i in user_roles:
                if use_slow_mode:
                    event.author.remove_role(list_colors[i])
                else:
                    del user_roles[i]
    else:
        # Check if a role should be removed
        for i in list_colors:
            if i in user_roles and i != role:
                if use_slow_mode:
                    event.author.remove_role(list_colors[i])
                else:
                    del user_roles[i]
        user_roles[role] = list_colors[role]

    if not use_slow_mode:
        repl_roles = []
        for i in user_roles:
            repl_roles.append(user_roles[i])

        event.author.replace_roles(repl_roles)
        return "Done!"
    else:
        if role != no_role:
            event.author.add_role(list_colors[role])
        return "Probably done."
