import os
from SpankyWorker import hook


@hook.periodic(3600*12)
def backup_data():
    os.system("cd storage_data && \
            git add -A && \
            git commit -m \"Update data\" && \
            git push")
