import platform
import psutil
import os
import time
from datetime import timedelta
from spanky.utils.filesize import size as format_bytes
from spanky.plugin import hook

@hook.command()
def system(send_message):
    """-- Retrieves information about the host system."""

    # Get general system info
    sys_os = platform.platform()
    python_implementation = platform.python_implementation()
    python_version = platform.python_version()
    sys_architecture = '-'.join(platform.architecture())
    sys_cpu_count = platform.machine()

    send_message(
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
    
    process = psutil.Process(os.getpid())

    # get the data we need using the Process we got
    cpu_usage = process.cpu_percent(1)
    thread_count = process.num_threads()
    memory_usage = format_bytes(process.memory_info()[0])
    uptime = timedelta(seconds=round(time.time() - process.create_time()))

    send_message(
        "Uptime: {}, "
        "Threads: {}, "
        "CPU Usage: {}, "
        "Memory Usage: {}"
        .format(
            uptime,
            thread_count,
            cpu_usage,
            memory_usage)
    )
