import os
import html
from spanky.plugin import hook
from spanky.plugin.permissions import Permission

@hook.command
def help(bot, text, event, send_embed):
    """Get help for a command or the help document"""
    if text in bot.plugin_manager.commands:
        send_embed(
                text, "",
                {"Usage:": bot.plugin_manager.commands[text].function.__doc__})
        return

    send_embed("Bot help:", "",
        {"Links:": "See <https://github.com/gc-plp/spanky-command-doc/blob/master/commands/%s/commands.md> for usable commands\nFor admin commands see <https://github.com/gc-plp/spanky-command-doc/blob/master/commands/%s/admin.md>" % (event.server.id, event.server.id)})
    return

def prepare_repo(storage_loc):
    dest = storage_loc + "/doc/"
    os.system("rm -rf %s" % dest)
    os.system("mkdir -p %s" % dest)
    os.system("git clone git@github.com:gc-plp/spanky-command-doc.git %s" \
        % (storage_loc + "/doc"))

def gen_doc(files, fname, header, bot, storage_loc, server_id):
    doc = header + "\n"
    for file in sorted(files):
        if len(files[file]) == 0:
            continue

        doc += "------\n"
        doc += "### %s \n" % file
        for cmd in sorted(files[file]):
            hook = bot.plugin_manager.commands[cmd]
            hook_name = " / ".join(i for i in hook.aliases)

            help_str = bot.plugin_manager.commands[cmd].function.__doc__

            if help_str:
                help_str = help_str.lstrip("\n").lstrip(" ").rstrip(" ").rstrip("\n")
            else:
                help_str = "No documentation provided."

            help_str = help_str.replace("\n", "\n\n")

            doc += "**%s**: %s\n\n" % (hook_name, html.escape(help_str))

    md_dest = "%s/doc/commands/%s/" % (storage_loc, server_id)
    os.system("mkdir -p %s" % (md_dest))

    doc_file = open("%s/%s" % (md_dest, fname), "w")
    doc_file.write(doc)

def commit_changes(storage_loc, server_id):
    server_path = "%s/doc/commands/%s" % (storage_loc, server_id)

    os.system("git -C %s add ." % server_path)
    os.system("git -C %s commit -m \"Update documentation for %s\"" % (server_path, server_id))
    os.system("git -C %s push" % (server_path))

@hook.command(permissions=Permission.admin)
def gen_documentation(bot, storage_loc, event):
    for server in bot.get_servers():
        files = {}
        admin_files = {}

        cmd_dict = bot.plugin_manager.commands
        for cmd_str in cmd_dict:
            cmd = cmd_dict[cmd_str]
            file_name = cmd.plugin.name.split("/")[-1].replace(".py", "")
            file_cmds = []

            if file_name not in files:
                files[file_name] = []

            if file_name not in admin_files:
                admin_files[file_name] = []

            if bot.plugin_manager.commands[cmd.name].server_id and not \
                    bot.plugin_manager.commands[cmd.name].has_server_id(server.id):
                print(cmd.name)
                continue

            if bot.plugin_manager.commands[cmd.name].permissions == Permission.admin:
                admin_files[file_name].append(cmd.name)
            elif bot.plugin_manager.commands[cmd.name].permissions == Permission.bot_owner:
                continue
            else:
                files[file_name].append(cmd.name)

        prepare_repo(storage_loc)
        gen_doc(files, "commands.md", "Bot commands:", bot, storage_loc, server.id)
        gen_doc(admin_files, "admin.md", "Admin commands:", bot, storage_loc, server.id)
        commit_changes(storage_loc, server.id)

    return "Done."
