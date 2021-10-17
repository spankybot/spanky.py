from spanky.hook2 import Hook, ActionCommand, Command
from spanky.hook2.hooklet import MiddlewareResult
from spanky.plugin.hook_parameters import map_params, extract_params

hook = Hook("legacy_compat_hook")


@hook.global_middleware(priority=4)
def check_format(action: ActionCommand, hooklet: Command):
    cmd_format = hooklet.args.get("format", None)
    if cmd_format == None:
        return MiddlewareResult.CONTINUE
    if len(cmd_format.split()) != len(action.text.split()):
        msg = "Invalid format"
        if hooklet.get_doc(no_format=True):
            msg += ": " + "\n`" + hooklet.get_doc().strip() + "`"
        return MiddlewareResult.DENY, msg


# cmd_args are used for image-related stuff
@hook.global_middleware(priority=4)
def command_args(action: ActionCommand, hooklet: Command):
    param_list = hooklet.args.get("params", None)
    if param_list == None:
        return
    param_list = extract_params(param_list)
    action.context["cmd_args"] = map_params(action.text, param_list)
    print(param_list, action.context)
