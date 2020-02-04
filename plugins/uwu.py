from spanky.plugin import hook

@hook.command()
def uwu(text):
    """
    <text> - translate text to UwU
    """
    text = text.replace('L', 'W')
    text = text.replace('R', 'W')
    text = text.replace('l', 'w')
    text = text.replace('r', 'w')
    text = text.replace("no", "nyo")
    text = text.replace("mo", "myo")
    text = text.replace("No", "Nyo")
    text = text.replace("Mo", "Myo")
    text = text.replace("na", "nya")
    text = text.replace("ni", "nyi")
    text = text.replace("nu", "nyu")
    text = text.replace("ne", "nye")
    text = text.replace("anye", "ane")
    text = text.replace("inye", "ine")
    text = text.replace("onye", "one")
    text = text.replace("unye", "une")
    return text + " uwu"
