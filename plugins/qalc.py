import subprocess
from spanky.plugin import hook


@hook.command()
def calc(text):
    """<expression> - qalc interface"""
    proc = subprocess.run(
        ["qalc", text], timeout=3, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    return "`%s`" % proc.stdout.decode()
