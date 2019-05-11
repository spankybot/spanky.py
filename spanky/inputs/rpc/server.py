import grpc

from spanky.inputs.rpc import spanky_pb2
from spanky.inputs.rpc.spanky_pb2_grpc import add_SpankyServicer_to_server, SpankyServicer
from concurrent import futures

class Servicer(SpankyServicer):
    def ExposeMethods(self, request, context):
        print(request)

        return spanky_pb2.AckCli(methods="plm")

    def DoWork(self, request_iterator, contex):
        try:
            print("DoWork call")

            for r in request_iterator:
                print(r.workThis)
                yield spanky_pb2.WorkRequest(workThis="plm")

            print("Aasda")
        except:
            import traceback
            traceback.print_exc()



server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
add_SpankyServicer_to_server(Servicer(), server)

server.add_insecure_port("[::]:5151")
server.start()

while True:
    import time
    time.sleep(10)
