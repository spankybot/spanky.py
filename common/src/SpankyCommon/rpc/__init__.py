import os
import pathlib
import sys

from grpc_tools import protoc


def generate_from_proto():
    """
    Helper function to generate code on the fly.
    Not to be used in production
    """
    # Save current path
    orig_path = os.getcwd()

    # Get script path
    crt_dir = pathlib.PurePath(os.path.realpath(__file__)).parent

    try:
        # Change dir to file location
        os.chdir(crt_dir)

        # Notes for figuring this out later!
        #
        # Since protobuf doesn't know how to generate relative imports, it
        # looks like referencing the proto file from inside multiple folders
        # will generate the code imports, relative to the protobuf file path.
        # e.g. /foo/bar/test.proto will generate "from foo.bar import ..."
        # So, we reference things two folders above to use the
        # actual package name.
        rv = protoc.main((
            '',
            '--python_out=../..',
            '--grpc_python_out=../..',
            '-Iproto',
            "proto/SpankyCommon/rpc/spanky.proto",
        ))

        if rv != 0:
            print("Error generating code! Exiting")
            sys.exit(1)
    except Exception as e:
        print(e)
    finally:
        # Change dir to initial location
        os.chdir(orig_path)