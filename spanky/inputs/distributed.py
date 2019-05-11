import grpc

from spanky.inputs.rpc import gen_code
from spanky.inputs.rpc import spanky_pb2
from spanky.inputs.rpc import spanky_pb2_grpc

bot = None

class Init():
    def __init__(self, bot_inst):
        global bot

        bot = bot_inst

    async def do_init(self):

        def send_requests():
            request_idx = 0
            while request_idx < 10:
                print(request_idx)
                request_idx += 1
                yield spanky_pb2.WorkRequest(workThis="ping " + str(request_idx))
                import time
                time.sleep(1)

        channel = grpc.insecure_channel('localhost:5151')
        stub = spanky_pb2_grpc.SpankyStub(channel)

        #caca = stub.ExposeMethods(spanky_pb2.NewCli(methods="asdasda"))
        #print(caca)

        try:
            while True:
                res = stub.DoWork(send_requests())
                for r in res:
                    print(r.workThis)

                import time
                time.sleep(1)
        except:
            import traceback
            traceback.print_exc()