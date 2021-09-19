from spanky.plugin import hook


@hook.command(params="float:hot float:crazy", format="hot crazy")
def vicky(cmd_args):
    """<hot> <crazy> - Returns the zone from the universal hot crazy matrix"""
    hot, crazy = cmd_args["hot"], cmd_args["crazy"]
    if hot < 0 or hot > 10 or crazy < 0 or crazy > 10:
        return "Invalid numbers"
    if hot >= 8 and crazy < 4:
        return "Tranny"
    if crazy < 4:
        return "Every woman is at least a 4 crazy"
    if hot < 5:
        return "No-go zone"
    if crazy >= hot:
        return "Danger zone"
    if hot <= 8:
        return "Fun zone"
    if crazy <= 5:
        return "Unicorns, they do not exist"
    if crazy <= 7:
        return "Wife zone"
    return "Date zone"
