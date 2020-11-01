from core import hook


@hook.command()
def test1():
    """test1"""
    return "test111"


@hook.command()
def test2():
    """test2"""
    return "test222"


#@hook.on_start()
def test3():
    """test3"""
    print("on_start")
    return "test333"
