import grpc
import json
import threading

# RPC stuff - maybe move it?
from rpc import gen_code
from rpc import spanky_pb2
from rpc import spanky_pb2_grpc

from core.manager import PluginManager
from database.db import db_data

from core.event import TextEvent
from core.permissions import PermissionMgr


class PythonWorker():
    def __init__(self):
        # Open the bot config file
        with open('bot_config.json') as data_file:
            self.config = json.load(data_file)

        print(f"Server: {self.config['server']}")

        self.server_conn = self.connect_to_server(self.config["server"])

        # Open the database first
        self.db = db_data(self.config.get('database', 'sqlite:///cloudbot.db'))

        # Create the plugin manager
        self.plugin_manager = PluginManager(
            self.config.get("plugin_paths", ""), self, self.db)

        # Register to the server
        register_resp = self.server_conn.NewPluginManager(
            spanky_pb2.NewPM(
                PluginMgrName="testplm"
            )
        )
        self.my_server_id = register_resp.PluginMgrID

        # Send the command list
        cmdlist_resp = self.server_conn.SetCommandList(
            spanky_pb2.ReqCmdList(
                PluginMgrID=self.my_server_id,
                CmdRequestList=self.plugin_manager.commands.keys()
            )
        )

        valid_commands = cmdlist_resp.CmdResponseList
        print(valid_commands)

    #     self.server_permissions = {}

    # def get_pmgr(self, server_id):
    #     """
    #     Get permission manager for a given server ID.
    #     """

    #     # Maybe the bot joined a server later
    #     if server_id not in self.server_permissions:
    #         server_list = {}

    #         for server in self.backend.get_servers():
    #             server_list[server.id] = server

    #         if server_id in server_list.keys():
    #             self.server_permissions[server_id] = \
    #                 PermissionMgr(server_list[server_id])

    #     return self.server_permissions[server_id]

    def send_message(self, text, channel_id):
        self.server_conn.SendMessage(spanky_pb2.SentMessage(
            channel_id=int(channel_id), text=text))

    class RemoteTextEvent():
        def reply(self, text):
            # TODO implement reply
            pass

    def run(self):
        for work in self.server_conn.HandleEvents(
            spanky_pb2.HandleEventsReq(
                PluginMgrID=self.my_server_id)):
            print(work)

            if work.msg.text[0] != ".":
                continue

            cmd_split = work.msg.text[1:].split(maxsplit=1)

            command = cmd_split[0]

            # Check if it's in the command list
            if command in self.plugin_manager.commands.keys():
                hook = self.plugin_manager.commands[command]

                if len(cmd_split) > 1:
                    event_text = cmd_split[1]
                else:
                    event_text = ""

                text_event = TextEvent(
                    hook=hook,
                    text=event_text,
                    triggered_command=command,
                    event=work.msg,
                    bot=self,
                    permission_mgr=None,
                    channel_id=work.msg.channel_id)

                self.run_in_thread(
                    target=self.plugin_manager.launch, args=(text_event,))

    def connect_to_server(self, server_addr):
        channel = grpc.insecure_channel('localhost:5151')
        stub = spanky_pb2_grpc.SpankyStub(channel)

        return stub

    def run_in_thread(self, target, args=()):
        thread = threading.Thread(target=target, args=args)
        thread.start()


PythonWorker().run()
