import os
import html
from spanky.plugin import hook
from spanky.plugin.permissions import Permission
import subprocess


@hook.command()
def help(bot, text, event, send_embed, reply):
    """Get help for a command or the help document"""
    if text in bot.plugin_manager.commands:
        send_embed(
            text, "", {"Usage:": bot.plugin_manager.commands[text].function.__doc__}
        )
        return

    reply(
        "Comenzi bot:\nComenzi generale - <https://mdmd.kilonova.ro/spankyfork/comenzi/%s/commands>\nComenzi administrative - <https://mdmd.kilonova.ro/spankyfork/comenzi/%s/admin>"
        % (event.server.id, event.server.id)
    )
    return


vropage = "/home/alexv/WebServer/knmd/content/spankyfork"
outDir = "/home/alexv/tempDir"


def send_off():
    return subprocess.check_output(
        "rsync -avP %s/ webServer:%s/" % (outDir, vropage), shell=True
    ).decode("utf-8")


def gen_doc(files, fname, header, bot, server_id):
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

    md_dest = "%s/comenzi/%s/" % (outDir, server_id)
    os.system("mkdir -p %s" % (md_dest))

    doc_file = open("%s/%s" % (md_dest, fname), "w")
    doc_file.write(doc)


@hook.command(permissions=Permission.bot_owner)
def gen_documentation(bot, event):
    out = ""
    for server in bot.get_servers():
        files = {}
        admin_files = {}

        cmd_dict = bot.plugin_manager.commands
        for cmd_str in cmd_dict:
            cmd = cmd_dict[cmd_str]
            file_name = cmd.plugin.name.split("/")[-1].replace(".py", "")
            file_cmds = []

            if "roddit" not in file_name:
                continue

            if file_name not in files:
                files[file_name] = []

            if file_name not in admin_files:
                admin_files[file_name] = []

            if bot.plugin_manager.commands[
                cmd.name
            ].server_id and not bot.plugin_manager.commands[cmd.name].has_server_id(
                server.id
            ):
                print(cmd.name)
                continue

            if Permission.admin in bot.plugin_manager.commands[cmd.name].permissions:
                admin_files[file_name].append(cmd.name)
            elif (
                Permission.bot_owner
                in bot.plugin_manager.commands[cmd.name].permissions
            ):
                continue
            else:
                files[file_name].append(cmd.name)

        gen_doc(files, "commands.md", "Bot commands:", bot, server.id)
        gen_doc(admin_files, "admin.md", "Admin commands:", bot, server.id)
    out += send_off() + "\nDone."

    return out
