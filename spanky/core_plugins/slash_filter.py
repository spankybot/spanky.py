from spanky.hook2 import Hook, ActionCommand, Command
from spanky.hook2.hooklet import MiddlewareResult
from spanky.hook2.event import EventType

hook = Hook("slashfilter_hook")



@hook.global_middleware(priority=1)
def check_slash_filter(action: ActionCommand, hooklet: Command):
    print(action._raw.type)
    slash_only = hooklet.args.get("slash_only", False)
    if not slash_only:
        return
    if action._raw.type != EventType.slash:
        return MiddlewareResult.DENY, "Command must be used as slash command"
