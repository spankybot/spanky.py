import os
import datetime

import plugins.selector as selector
import spanky.utils.discord_utils as dutils

from spanky.plugin import hook, permissions
from spanky.plugin.permissions import Permission
from spanky.utils.volatile import set_vdata, get_vdata


# selector.py is the generic implementation of the selector
# role_selector.py is the plugin that manages the selectors

#
# Selector registration
#


def register_cmd(cmd, server):
    """Register a user defined command"""

    def create_it(cmd):
        async def do_cmd(text, server, storage, event, send_embed, reply):
            print(f"Got selector {cmd['name']}")
            if cmd["roles"] == []:
                # TODO: For some reason, return does not work here
                reply("No roles in selector")

            sel = selector.RoleSelector(
                server=server,
                title=cmd["title"],
                roles=cmd["roles"],
                max_selectable=cmd["maxSelectable"],
                paged=True,
            )
            await sel.do_send(event)

        do_cmd.__doc__ = cmd["description"]
        do_cmd.__name__ = cmd["name"]
        return do_cmd

    globals()[cmd["name"]] = hook.command(server_id=server.id)(create_it(cmd))


def reload_file(bot):
    dirname = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
    fname = os.path.basename(os.path.abspath(__file__))

    # TODO: use unified way of identifying plugins
    bot.plugin_manager.load_plugin(dirname + "/" + fname)


@hook.on_connection_ready()
def init_cmds(bot):
    """Register all commands on bot ready"""
    print("Connection ready")
    for server in bot.backend.get_servers():
        storage = bot.server_permissions[server.id].get_plugin_storage(
            "plugins_role_selector.json"
        )
        if "selectors" not in storage or storage["selectors"] == {}:
            continue

        for cmd in storage["selectors"]:
            print(f"[{server.id}] Registering {cmd}")
            register_cmd(storage["selectors"][cmd], server)

    # TODO: workaround - look into adding commands dinamically
    if not get_vdata("selector_reload"):
        print("selector_reload")
        set_vdata("selector_reload", True)
        reload_file(bot)


#
# Selector modifiers
#


@hook.command(permissions=Permission.admin)
def set_selector_description(server, storage, text, bot):
    """<selector> <description> - sets a description for the selector documentation"""
    text = text.split(maxsplit=1)
    if len(text) < 2:
        return "Format: " + set_selector_description.__doc__

    if "selectors" not in storage or storage["selectors"] == {}:
        return "No selectors available"

    if text[0] not in storage["selectors"]:
        return "Invalid selector"

    storage["selectors"][text[0]]["description"] = text[1]
    storage.sync()

    reload_file(bot)

    return "Done"


@hook.command(permissions=Permission.admin)
def set_selector_max_selectable(server, storage, text, bot):
    """<selector> <maxSelectable (int)> - sets the number of max selectable options for the selector. If maxSelectable <= 0, then the number of max selectable options is unlimited"""
    text = text.split()
    if len(text) != 2:
        return "Format: " + set_selector_max_selectable.__doc__

    if "selectors" not in storage or storage["selectors"] == {}:
        return "No selectors available"

    if text[0] not in storage["selectors"]:
        return "Invalid selector"

    if not text[1].isdigit():
        return "The number of maximum selectables must be... well... a number"

    storage["selectors"][text[0]]["maxSelectable"] = int(text[1])
    storage.sync()

    reload_file(bot)

    return "Done"


@hook.command(permissions=Permission.admin)
def set_selector_title(server, storage, text, bot):
    """<selector> <title> - sets a title for the selector"""
    text = text.split(maxsplit=1)
    if len(text) < 2:
        return "Format: " + set_selector_title.__doc__

    if "selectors" not in storage or storage["selectors"] == {}:
        return "No selectors available"

    if text[0] not in storage["selectors"]:
        return "Invalid selector"

    storage["selectors"][text[0]]["title"] = text[1]
    storage.sync()

    reload_file(bot)

    return "Done"


@hook.command(permissions=Permission.admin)
def add_selector_roles(server, storage, text, bot, str_to_id):
    """<selector> <roles> - adds the specified roles to the selector """
    text = text.split()
    if len(text) < 2:
        return "Format: " + add_selector_roles.__doc__

    selector = text[0]
    print(text)

    if "selectors" not in storage or storage["selectors"] == {}:
        return "No selectors available"

    if selector not in storage["selectors"]:
        return "Invalid selector"

    for i in text[1:]:
        role = dutils.get_role_by_id(server, str_to_id(i))
        if role == None:
            continue
        storage["selectors"][selector]["roles"].append(role.id)

    storage["selectors"][selector]["roles"] = list(
        set(storage["selectors"][selector]["roles"])
    )

    storage.sync()

    reload_file(bot)

    return "Done"


@hook.command(permissions=Permission.admin)
def add_selector_role_interval(server, storage, text, bot, str_to_id):
    """<selector> <role start> <role end> - adds the roles in the specified interval to the selector """
    text = text.split()
    if len(text) < 2:
        return "Format: " + add_selector_roles.__doc__

    selector = text[0]
    print(text)

    if "selectors" not in storage or storage["selectors"] == {}:
        return "No selectors available"

    if selector not in storage["selectors"]:
        return "Invalid selector"

    roles = dutils.get_roles_between_including(
        str_to_id(text[1]), str_to_id(text[2]), server
    )

    for role in roles:
        storage["selectors"][selector]["roles"].append(role.id)

    storage["selectors"][selector]["roles"] = list(
        set(storage["selectors"][selector]["roles"])
    )

    storage.sync()

    reload_file(bot)

    return "Done"


@hook.command(permissions=Permission.admin)
def remove_selector_role_interval(server, storage, text, bot, str_to_id):
    """<selector> <role start> <role end> - removes the roles in the specified interval from the selector.
    NOTE: THIS REMOVES THE ROLE INTERVAL FROM THE ROLE LIST, NOT FROM THE SELECTOR LIST. """
    text = text.split()
    if len(text) < 2:
        return "Format: " + remove_selector_role_interval.__doc__

    selector = text[0]
    print(text)

    if "selectors" not in storage or storage["selectors"] == {}:
        return "No selectors available"

    if selector not in storage["selectors"]:
        return "Invalid selector"

    roles = dutils.get_roles_between_including(
        str_to_id(text[1]), str_to_id(text[2]), server
    )

    cmd = storage["selectors"][selector]

    roles = [role.id for role in roles]
    oldroles = cmd["roles"]
    newroles = [role for role in oldroles if role not in roles]

    cmd["roles"] = list(set(newroles))

    storage["selectors"][selector] = cmd

    storage.sync()

    reload_file(bot)

    return "Done"


@hook.command(permissions=Permission.admin)
def remove_selector_roles(server, storage, text, bot, str_to_id):
    """<selector> <roles> - removes the specified roles from the selector """
    text = text.split()
    if len(text) < 2:
        return "Format: " + remove_selector_roles.__doc__

    selector = text[0]
    print(text)

    if "selectors" not in storage or storage["selectors"] == {}:
        return "No selectors available"

    if selector not in storage["selectors"]:
        return "Invalid selector"

    for i in text[1:]:
        role = dutils.get_role_by_id(server, str_to_id(i))
        if role == None:
            continue
        try:
            storage["selectors"][selector]["roles"].remove(role.id)
        except:
            pass
    storage["selectors"][selector]["roles"] = list(
        set(storage["selectors"][selector]["roles"])
    )

    storage.sync()

    reload_file(bot)

    return "Done"


#
# Selector creation, listing and deletion
#


@hook.command(permissions=Permission.admin)
def create_selector(text, str_to_id, server, bot, storage):
    """<selector name> - create a selector that assigns a role"""

    if " " in text or text[0].isdigit():
        return "Invalid selector name"

    # Check if length is correct
    if len(text) < 2:
        return create_selector.__doc__

    cmd = text
    # Check minumum length
    if len(cmd) < 5:
        return "Selector command length needs to be at least 5."

    # Check that command exists
    if cmd in bot.plugin_manager.commands:
        return f"Command {cmd} already exists. Try using another name."

    # initialize command
    if "selectors" not in storage:
        storage["selectors"] = {}

    # Create new object
    new_cmd = {}
    new_cmd["name"] = cmd
    new_cmd["roles"] = []
    new_cmd["title"] = ""
    new_cmd["description"] = "selector command as defined by server ops."
    new_cmd["maxSelectable"] = 0

    storage["selectors"][cmd] = new_cmd
    storage.sync()

    register_cmd(new_cmd, server)
    reload_file(bot)

    return "Done"


@hook.command()
def list_selectors(storage):
    """list selector commands"""
    if "selectors" not in storage or storage["selectors"] == {}:
        return "No selectors available"
    else:
        return "Available selectors: " + ", ".join(
            f'`{cmd["name"]}`' for cmd in storage["selectors"].values()
        )


@hook.command(permissions=Permission.admin)
def delete_selector(storage, text, bot):
    """<command_name> - delete a temporary selector command"""
    if "selectors" not in storage or storage["selectors"] == {}:
        return "No selectors available"

    for cmd in storage["selectors"].values():
        if cmd["name"] == text:
            # Remove plugin entry from the bot and globals
            # del bot.plugin_manager.commands[text]
            del globals()[cmd["name"]]
            del storage["selectors"][cmd["name"]]

            storage.sync()

            reload_file(bot)

            return "Done"

    return "Command not registered"
