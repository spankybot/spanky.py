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

@hook.command()
def system(reply, message):
    """-- Retrieves information about the host system."""

    # Get general system info
    sys_os = platform.platform()
    python_implementation = platform.python_implementation()
    python_version = platform.python_version()
    sys_architecture = '-'.join(platform.architecture())
    sys_cpu_count = platform.machine()

    reply(
        "OS: \x02{}\x02, "
        "Python: \x02{} {}\x02, "
        "Architecture: \x02{}\x02 (\x02{}\x02)"
        .format(
            sys_os,
            python_implementation,
            python_version,
            sys_architecture,
            sys_cpu_count)
    )
