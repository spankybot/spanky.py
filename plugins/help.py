from spanky.plugin import hook
from spanky.plugin.permissions import Permission

@hook.command
def help(bot, text):
    """Get help for a command or the help document"""
    if text in bot.plugin_manager.commands:
        return "`%s:` " % text + bot.plugin_manager.commands[text].function.__doc__
    
    return "TODO help doc"

@hook.command(permissions=Permission.admin)
def gen_documentation(bot):
    files = {}
    
    cmd_dict = bot.plugin_manager.commands
    for cmd_str in cmd_dict:
        cmd = cmd_dict[cmd_str]
        file_name = cmd.plugin.name.split("/")[-1].replace(".py", "")
        
        if file_name not in files:
            files[file_name] = []
        files[file_name].append(cmd.name)
            
    sorted_files = sorted(files.keys())
    
    doc = "# Commands:"
    for file in sorted_files:
        doc += "***\n"
        doc += "#### %s \n" % file
        for cmd in files[file]:
            hook = bot.plugin_manager.commands[cmd]
            hook_name = " / ".join(i for i in hook.aliases)
            
            help_str = bot.plugin_manager.commands[cmd].function.__doc__
            
            if help_str:
                help_str = help_str.lstrip("\n").lstrip(" ").rstrip(" ").rstrip("\n")
            else:
                help_str = "No documentation provided."
            
            doc += "**%s**: %s\n\n" % (hook_name, help_str)
            
    print(doc)
