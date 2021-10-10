from spanky.hook2 import Hook, EventType, ComplexCommand

# Așa creem un hook pentru acest plugin
hook = Hook("hook2_example_plugin")


"""
Un mic ghid pentru schimbarile mai mari:

@hook.on_connection_ready -> @hook.event(EventType.on_conn_ready)
@hook.on_ready -> @hook.event(EventType.on_ready)
@hook.on_start -> @hook.event(EventType.on_start)
"""


@hook.command()
def test_hook2(reply):
    reply("COMMAND EXECUTED WITH HOOK2")


# test_cmd se ataseaza la hook și definim ulterior subcomenzile (și help-ul, care e fallback pentru nicio comandă și subcomandă invalidă)
test_cmd = ComplexCommand(hook, "test_cmd")


@test_cmd.subcommand()
def subcmd():
    return "Cf"


@test_cmd.subcommand()
def subcmd2():
    return "Subcomandă"


@test_cmd.help()
def help():
    return "Help suprascris"
