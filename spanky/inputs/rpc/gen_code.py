from grpc_tools import protoc

protodir = "spanky/inputs/rpc/"

protoc.main(
    (
        "",
        "--python_out=.",
        "--grpc_python_out=.",
        protodir + "spanky.proto",
    )
)
