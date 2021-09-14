from spanky.hook2 import Hook, ActionCommand, Command
from spanky.hook2.hooklet import MiddlewareResult

hook = Hook("permission_hook")

# Permission context creation and validation

@hook.global_middleware(priority=0)
def setup_perm_ctx(action: ActionCommand, hooklet: Command):
    action.context["perms"] = {"creds": []}

@hook.global_middleware(priority=1000000)
def finalize_perm_filter(action: ActionCommand, hooklet: Command):
    perms = set(hooklet.args.get('permissions', []))
    if perms == set():
        return MiddlewareResult.CONTINUE
    if perms & set(action.context["perms"]["creds"]):
        return MiddlewareResult.CONTINUE
    return MiddlewareResult.DENY

# Permissions

@hook.global_middleware(priority=10)
def perm_bot_owner(action: ActionCommand, hooklet: Command):
    if action.author.id in action.bot.config.get("bot_owners", []):
        action.context["perms"]["creds"].append("bot_owner")

@hook.global_middleware(priority=10)
def perm_admin(action: ActionCommand, hooklet: Command, storage):
    if 'admin_roles' not in storage:
        if hooklet.args.get('permissions', None) != None:
            action.reply("Warning! Admin not set! Use .add_admin_role to set an administrator.", check_old=False)
    else:
        # TODO: command_owners (maybe in another middleware?)
        allowed_roles = set(storage["admin_roles"])
        user_roles = set([i.id for i in action.author.roles])
        if user_roles & allowed_roles:
            action.context["perms"]["creds"].append("admin")

@hook.command(permissions="admin")
def migrate_admin_storage(storage):
    return "TODO"

@hook.command(permissions="admin")
def add_admin_role(storage):
    return "TODO"

@hook.command(permissions="admin")
def get_admin_roles(storage):
    return "TODO"

@hook.command(permissions="admin")
def remove_admin_role(storage):
    return "TODO"

@hook.global_middleware(priority=1)
def check_server_id(action: ActionCommand, hooklet: Command):
    good_server = True
    server_id = hooklet.args.get("server_id", None)
    if server_id == None:
        return MiddlewareResult.CONTINUE
    if isinstance(server_id, int):
        server_id = str(server_id)
    if type(server_id) == str:
        good_server = action.server_id == server_id
    elif type(server_id) == list:
        good_server = action.server_id in server_id
    else:
        print(f"Unknown server_id type for hooklet {hooklet.hooklet_id}")
        good_server = False
    if not good_server:
        print(good_server, action.server_id is server_id, action.server_id == server_id, type(action.server_id), type(server_id), action.server_id, server_id)
        return MiddlewareResult.DENY
    return MiddlewareResult.CONTINUE
