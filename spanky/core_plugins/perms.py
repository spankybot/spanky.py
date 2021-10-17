from spanky.hook2 import (
    Hook,
    ActionCommand,
    Command,
    ComplexCommand,
    MiddlewareResult,
)

hook = Hook("permission_hook", storage_name="plugins_admin")

# Permission context creation and validation


@hook.global_middleware(priority=0)
def setup_perm_ctx(action: ActionCommand, hooklet: Command):
    action.context["perms"] = {"creds": []}


@hook.global_middleware(priority=100)
def finalize_perm_filter(action: ActionCommand, hooklet: Command):
    perms = hooklet.args.get("permissions", [])
    if not isinstance(perms, list):
        perms = [perms]
    new_perms = []
    for perm in perms:
        if hasattr(perm, "value"):
            new_perms.append(perm.value)
        else:
            new_perms.append(perm)
    perms = set(new_perms)
    if perms == set():
        return MiddlewareResult.CONTINUE
    if perms & set(action.context["perms"]["creds"]):
        return MiddlewareResult.CONTINUE
    return MiddlewareResult.DENY, "You aren't allowed to do that"


# Permissions


@hook.global_middleware(priority=10)
def perm_bot_owner(action: ActionCommand, hooklet: Command):
    if action.author.id in action.bot.config.get("bot_owners", []):
        action.context["perms"]["creds"].append("bot_owner")


@hook.global_middleware(priority=10)
def perm_admin(action: ActionCommand, hooklet: Command):
    storage = hook.server_storage(action.server_id)
    if "admin_roles" not in storage or len(storage["admin_roles"]) == 0:
        if hooklet.args.get("permissions", None) != None:
            action.reply(
                "Warning! Admin not set! Use .admin_role add to set an administrator.",
                check_old=False,
            )
            action.context["perms"]["creds"].append("admin")
    else:
        allowed_roles = set(storage["admin_roles"])
        user_roles = set([i.id for i in action.author.roles])
        if user_roles & allowed_roles:
            action.context["perms"]["creds"].append("admin")
