from spanky.hook2 import Hook, ActionCommand, Command
from spanky.hook2.hooklet import MiddlewareResult

hook = Hook("serverid_hook", storage_name="plugins_admin.json")


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
        return MiddlewareResult.DENY
