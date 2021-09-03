from spanky.hook2 import Hook, ActionCommand, Command
from spanky.hook2.hooklet import MiddlewareResult

hook = Hook("permission_hook")

@hook.global_middleware(priority=0)
def setup_perm_ctx(action: ActionCommand, hooklet: Command):
    action.context["perms"] = {}

@hook.global_middleware(priority=1000000)
def finalize_perm_filter(action: ActionCommand, hooklet: Command):
    print('cf')
    pass

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
