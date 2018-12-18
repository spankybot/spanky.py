import os
import time
import platform
from datetime import timedelta

from spanky.plugin import hook

import time
i = 0
@hook.periodic(1)
def checker(bot):
    global i
    i += 1
    x = i
    print("" + str(x))
    time.sleep(1)
    print("        " + str(x))
    
    
@hook.periodic(1)
def checker2(bot):
    print("xxx")

@hook.on_start()
def checker3():
    print("121")

@hook.command
def test2(message, text, nick):
    message("asdadasadsadsas")

@hook.command()
def system(message):
    """-- Retrieves information about the host system."""

    # Get general system info
    sys_os = platform.platform()
    python_implementation = platform.python_implementation()
    python_version = platform.python_version()
    sys_architecture = '-'.join(platform.architecture())
    sys_cpu_count = platform.machine()

    message(
        "OS: {}, "
        "Python: {} {}, "
        "Architecture: {} ({})"
        .format(
            sys_os,
            python_implementation,
            python_version,
            sys_architecture,
            sys_cpu_count)
    )
