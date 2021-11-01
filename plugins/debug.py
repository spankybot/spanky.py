from spanky.hook2 import Hook

hook = Hook("debug_cmds")

@hook.command(permissions="bot_owner")
def inspect_hook(hook: Hook, text: str):
    if text == "":
        text = "bot_hook"
    hk = hook.root.find_hook(text)
    if not hk:
        return "Hook doesn't exist"
    info = f"""
Name: {hk.hook_id}
Children ({len(hk.children)}): {', '.join([child.hook_id for child in hk.children])}
Comands ({len(hk.commands)}): {', '.join([cmd.name for cmd in hk.commands.values()])}
Event Handlers ({len(hk.events)}): {', '.join([' '.join((name, hklt.event_type.name)) for name, hklt in hk.events.items()])}
Periodics ({len(hk.periodics)}): {', '.join(hk.periodics.keys())}
"""
    return info
