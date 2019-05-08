def roles_from_list(start_role, end_role, remove_text, send_message, server, event, bot, text):
    use_slow_mode = False

    bot_roles = bot.get_bot_roles_in_server(server)

    list_colors = {remove_text.lower(): None}
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

    # Get starting and ending positions of listed roles
    for srole in server.get_roles():
        if start_role in srole.name:
            pos_start = srole.position
        if end_role in srole.name:
            pos_end = srole.position

    # List available roles
    for i in server.get_roles():
        if i.position > pos_end and i.position < pos_start:
            list_colors[i.name.lower()] = i

    # If no role was specified, just print them
    if text == "":
        send_message("Available roles: `%s`" % (", ".join(i for i in sorted(list_colors))))
        return

    split = text.split()
    role = " ".join(split).lower()

    # Check if the requested role exists
    if role not in list_colors:
        send_message("%s is not a role. Available roles: `%s`" % (role, ", ".join(i for i in sorted(list_colors))))
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
        return "Ai mai multe drepturi decat mine si s-ar putea sa nu fi mers totul OK. Fa-l singur in plm."
