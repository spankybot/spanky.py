from spanky.hook2 import Hook, ActionCommand, Command
from spanky.hook2.hooklet import MiddlewareResult

hook = Hook("pm_hook")


@hook.global_middleware(priority=5)
def handle_pm(action: ActionCommand, hooklet: Command):
    can_pm = hooklet.args.get("can_pm", False)
    pm_only = hooklet.args.get("pm_only", False)
    if pm_only:
        can_pm = True
    if action.is_pm and not can_pm:
        return MiddlewareResult.DENY, "Command cannot be run in DM"
    if not action.is_pm and pm_only:
        return MiddlewareResult.DENY, "Command can only be run in DM"
