from core import hook


@hook.command()
def test1():
    """test1"""
    return "test111"


@hook.command()
def test2():
    """test2"""
    return "test222"


@hook.command()
def test3():
    """test3"""
    return "test333"
