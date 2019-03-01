from spanky.plugin import hook

@hook.command()
def e(event):
    """Expand an emoji"""
    return " ".join(event.url)
