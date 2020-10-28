import sys

from grpc_tools import protoc

protodir = "rpc/"

rv = protoc.main((
    '',
    '--python_out=.',
    '--grpc_python_out=.',
    protodir + 'spanky.proto',
))

if rv != 0:
    print("Error generating code")
    sys.exit(1)