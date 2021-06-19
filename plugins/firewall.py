from spanky.plugin import hook
from spanky.plugin.event import EventType
from spanky.plugin.permissions import Permission

from spanky.utils import time_utils
from spanky.utils.cmdparser import CmdParser


@hook.periodic(1, initial_interval=1)
def firewall_check(bot):
    for server in bot.backend.get_servers():
        storage = bot.server_permissions[server.id].get_plugin_storage(
            "plugins_firewall.json")

        if "fw" not in storage:
            continue

        if storage["fw"]["status"] == "up" and storage["fw"]["end_time"] and time_utils.tnow() > storage["fw"]["end_time"]:
            storage["fw"]["status"] = "auto stopped on %s GMT" % time_utils.time_to_date(
                storage["fw"]["end_time"])
            storage.sync()


@hook.event(EventType.join)
def fw_on_join(event, storage, server):
    if "fw" not in storage:
        return

    if storage["fw"]["status"] == "up":
        if storage["fw"]["mode"] == "autokick":
            event.member.kick()
        elif storage["fw"]["mode"] == "autoban":
            event.member.ban(server)


@hook.command(permissions=Permission.admin)
def firewall(text, reply, storage):
    """
    Manage server firewall.

    Usage:
        - up [expire_time]
        - down
        - status
        - mode autokick|autoban

    Examples:
        .firewall up -> will raise the firewall indefinitely
        .firewall up 10s -> will raise the firewall for 10 seconds
        .firewall up 1h -> will raise the firewall for one hour

        .firewall mode autokick -> enables autokick for the firewall.
    """

    if "fw" not in storage:
        fw = {
            "mode": "autokick",
            "status": "down",
            "start_time": 0,
        }
        storage["fw"] = fw
        storage.sync()

    def fw_up(text):
        # Extract the duration
        if len(text) > 0:
            storage["fw"]["end_time"] = time_utils.tnow(
            ) + time_utils.timeout_to_sec(text[0])
        else:
            storage["fw"]["end_time"] = None

        storage["fw"]["status"] = "up"
        storage.sync()

        if storage["fw"]["end_time"]:
            reply("Firewall enabled. It will stop in %s" %
                  time_utils.sec_to_human(time_utils.timeout_to_sec(text[0])))
        else:
            reply("Firewall enabled. It will run indefinitely.")

    def fw_down(text):
        storage["fw"]["status"] = "down"
        storage.sync()

        reply("Firewall disabled.")

    def fw_status(text):
        to_reply = "```\n" + "Firewall status: " + storage["fw"]["status"]
        to_reply += "\nFirewall mode: " + storage["fw"]["mode"]

        if storage["fw"]["status"] == "up":
            if storage["fw"]["end_time"]:
                to_reply += "\nFirewall will stop at: %s GMT" % time_utils.time_to_date(
                    storage["fw"]["end_time"])
            else:
                to_reply += "\nFirewall does not have a timeout and will run indefinitely."

        to_reply += "\n```"
        reply(to_reply)

    def fw_mode(text):
        storage["fw"]["mode"] = text[0]
        reply("Firewall set to: " + text[0])

    parser = CmdParser(
        "firewall",
        "operate the firewall",
        args=[
            CmdParser(
                "command",
                "firewall command",
                options=[
                    CmdParser(
                        "up",
                        "raise firewall",
                        args=[CmdParser(
                            "duration",
                            "how long to keep the firewall up",
                            required=False,
                            default=0)],
                        action=fw_up),
                    CmdParser(
                        "down",
                        "disable firewall",
                        action=fw_down),
                    CmdParser(
                        "status",
                        "view firewall status",
                        action=fw_status),
                    CmdParser(
                        "mode",
                        "set firewall mode",
                        options=[
                            CmdParser(
                                "autokick", "autokick while firewall is up"),
                            CmdParser("autoban", "autoban while firewall is up")],
                        action=fw_mode
                    ),
                ]
            )
        ]
    )

    try:
        parser.parse(text)
    except CmdParser.HelpException as e:
        return "```\n" + str(e) + "\n```"
    except CmdParser.Exception as e:
        return "```\n" + str(e) + "\n```"
