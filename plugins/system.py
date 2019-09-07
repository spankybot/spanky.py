import platform
import psutil
import os
import time
import tracemalloc
import linecache
from datetime import timedelta
from spanky.utils.filesize import size as format_bytes
from spanky.plugin.permissions import Permission
from spanky.plugin import hook

start_trace = None

@hook.command()
def about():
    """
    Get about.
    """
    return "Bot source code can be found at https://github.com/gc-plp/spanky.py or ask the owner: plp#9999"

@hook.command()
def invite_me():
    """
    Get invitation for bot
    """
    return "https://discordapp.com/oauth2/authorize?&client_id=295665055117344769&scope=bot&permissions=0"

@hook.command(permissions=Permission.admin)
def start_tracemalloc():
    global start_trace

    tracemalloc.start(100)
    start_trace = tracemalloc.take_snapshot()

@hook.command(permissions=Permission.admin)
def stop_tracemalloc():
    tracemalloc.stop()

@hook.command(permissions=Permission.admin)
def mem_snapshot():
    key_type='lineno'
    limit=10

    rval = '#\n'
    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.compare_to(start_trace, key_type)

    # snapshot = snapshot.filter_traces((
    #     tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
    #     tracemalloc.Filter(False, "<unknown>"),
    # ))

    rval += "Top %s lines\n" % limit
    for index, stat in enumerate(top_stats[:limit], 1):
        frame = stat.traceback[0]
        # replace "/path/to/module/file.py" with "module/file.py"
        filename = os.sep.join(frame.filename.split(os.sep)[-2:])
        rval += "#%s: %s:%s: %.1f KiB\n" % (index, filename, frame.lineno, stat.size / 1024)

        line = linecache.getline(frame.filename, frame.lineno).strip()
        if line:
            rval += '    %s\n' % line

    other = top_stats[limit:]
    if other:
        size = sum(stat.size for stat in other)
        rval += "%s other: %.1f KiB\n" % (len(other), size / 1024)
    total = sum(stat.size for stat in top_stats)
    rval += "Total allocated size: %.1f KiB\n" % (total / 1024)

    return rval

@hook.command()
def system(send_message):
    """-- Retrieves information about the host system."""

    # Get general system info
    sys_os = platform.platform()
    python_implementation = platform.python_implementation()
    python_version = platform.python_version()
    sys_architecture = '-'.join(platform.architecture())
    sys_cpu_count = platform.machine()

    msg = "OS: {}, "\
        "Python: {} {}, "\
        "Architecture: {} ({})".format(
            sys_os,
            python_implementation,
            python_version,
            sys_architecture,
            sys_cpu_count)

    process = psutil.Process(os.getpid())

    # get the data we need using the Process we got
    cpu_usage = process.cpu_percent(1)
    thread_count = process.num_threads()
    memory_usage = format_bytes(process.memory_info()[0])
    uptime = timedelta(seconds=round(time.time() - process.create_time()))

    msg += "Uptime: {}, "\
        "Threads: {}, "\
        "CPU Usage: {}, "\
        "Memory Usage: {}".format(
            uptime,
            thread_count,
            cpu_usage,
            memory_usage)

    return msg
