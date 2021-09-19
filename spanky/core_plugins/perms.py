from spanky.hook2 import (
    Hook,
    ActionCommand,
    Command,
    ComplexCommand,
    MiddlewareResult,
)
from discord import AllowedMentions

no_mention = AllowedMentions.none()


hook = Hook("permission_hook", storage_name="plugins_admin.json")

# Permission context creation and validation


@hook.global_middleware(priority=0)
def setup_perm_ctx(action: ActionCommand, hooklet: Command):
    action.context["perms"] = {"creds": []}


@hook.global_middleware(priority=100)
def finalize_perm_filter(action: ActionCommand, hooklet: Command):
    perms = hooklet.args.get("permissions", [])
    if not isinstance(perms, list):
        perms = [perms]
    perms = set(perms)
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
def perm_admin(action: ActionCommand, hooklet: Command):
    storage = hooklet.hook.server_storage(action.server_id)
    if "admin_roles" not in storage or len(storage["admin_roles"]) == 0:
        if hooklet.args.get("permissions", None) != None:
            action.reply(
                "Warning! Admin not set! Use .admin_role add to set an administrator.",
                check_old=False,
            )
            action.context["perms"]["creds"].append("admin")
    else:
        # TODO: command_owners (maybe in another middleware?)
        allowed_roles = set(storage["admin_roles"])
        user_roles = set([i.id for i in action.author.roles])
        if user_roles & allowed_roles:
            action.context["perms"]["creds"].append("admin")


admin_cmd = ComplexCommand(hook, "admin_role", permissions="admin")


@admin_cmd.subcommand()
def add(str_to_id, text, storage):
    if "admin_roles" not in storage:
        storage["admin_roles"] = []
        storage.sync()
    text = str_to_id(text)
    if text in storage["admin_roles"]:
        return "Role is already an admin role!"
    storage["admin_roles"].append(text)
    storage.sync()
    return "Role added."


# am schimbat din list in list_roles pentru a nu suprascrie tipul
@admin_cmd.subcommand(name="list")
def list_roles(reply, storage, id_to_role_name):
    if "admin_roles" not in storage or len(storage["admin_roles"]) == 0:
        return "No admin roles set."
    reply(
        ", ".join([id_to_role_name(id) for id in storage["admin_roles"]]),
        allowed_mentions=no_mention,
    )


@admin_cmd.subcommand()
def remove(storage, text, str_to_id):
    text = str_to_id(text)
    if "admin_roles" not in storage:
        storage["admin_roles"] = []
        storage.sync()
    if text not in storage["admin_roles"]:
        return "Role is not an admin role!"

    storage["admin_roles"].remove(text)
    storage.sync()

    return "Admin role removed."


@admin_cmd.help()
def help():
    return "Usage: .admin_role <add|list|remove>"
