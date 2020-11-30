from SpankyWorker import hook


@hook.command()
def test1(reply):
    """test1"""

    reply("(local) a")

    return "(local) test111"


# @hook.periodic(2)
# async def test2(send_message):
#     """test2"""
#     print("Asdx")

#     return "test222"


@hook.on_start()
def test3():
    """test3"""
    print("on_start")
    return "test333"


@hook.on_ready()
def test4():
    """test4"""
    print("on_ready")
    return "test444"
