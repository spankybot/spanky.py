from spanky.hook2.arg_parser import *

def test1():
    result = parse(":sarg a1 ['a1', a2]: str = a1 | descr1 asdasda")[0]

    values = result.validate()

    assert values[PName.name] == 'a1'
    assert values[PChoice.name] == ['a1', 'a2']
    assert values[PArgType.name] == str
    assert values[PDefaultVal.name] == "a1"
    assert values[PDescription.name] == 'descr1 asdasda'


def test1_n1():
    try:
        parse(":sarg a1 ['a1', a2")
    except TokenError:
        return

    raise AssertionError("No error thrown")


def test1_n2():
    try:
        parse(":sarg a1 ['a1")
    except TokenError:
        return

    raise AssertionError("No error thrown")


def test1_n3():
    try:
        result = parse(":sarg a1 ['a1', a2]: int = 1 | descr1 asdasda")[0]
        result.validate()
    except ValueError:
        return

    raise AssertionError("No error thrown")


def test2():
    result = parse(":sarg a2 [1, 2]: int = -2 | descr2 asdasda")[0]
    values = result.validate()

    assert values[PName.name] == 'a2'
    assert values[PChoice.name] == [1, 2]
    assert values[PArgType.name] == int
    assert values[PDefaultVal.name] == 2
    assert values[PDescription.name] == 'descr2 asdasda'


def test3():
    result = parse(":sarg a3: int = 3 | descr3 asdasda")[0]
    values = result.validate()

    assert values[PName.name] == 'a3'
    assert values[PArgType.name] == int
    assert values[PDefaultVal.name] == 3
    assert values[PDescription.name] == 'descr3 asdasda'


def test4():
    result = parse(":sarg a4: str = 4 | descr4 asdasda")[0]
    values = result.validate()

    assert values[PName.name] == 'a4'
    assert values[PArgType.name] == str
    assert values[PDefaultVal.name] == '4'
    assert values[PDescription.name] == 'descr4 asdasda'


def test5():
    result = parse(":sarg a5: chan | descr5 asdasda")[0]
    values = result.validate()

    assert values[PName.name] == 'a5'
    assert values[PArgType.name] == 'chan'
    assert values[PDescription.name] == 'descr5 asdasda'


def test6():
    result = parse(":sarg a6 | descr6 asdasda")[0]
    values = result.validate()

    assert values[PName.name] == 'a6'
    assert values[PArgType.name] == str
    assert values[PDescription.name] == 'descr6 asdasda'


def test7():
    result = parse(":sarg a7")[0]
    values = result.validate()

    assert values[PName.name] == 'a7'
    assert values[PArgType.name] == str


def test8():
    result = parse(":sarg a8 [1, 2]")[0]
    values = result.validate()

    assert values[PName.name] == 'a8'
    assert values[PChoice.name] == ['1', '2']
    assert values[PArgType.name] == str


def test9():
    result = parse(":sarg a9 = 0.5")[0]
    values = result.validate()

    assert values[PName.name] == 'a9'
    assert values[PArgType.name] == str
    assert values[PDefaultVal.name] == "0.5"


def test10():
    result = parse(":sarg a10: float = 0.5")[0]
    values = result.validate()

    assert values[PName.name] == 'a10'
    assert values[PArgType.name] == float
    assert values[PDefaultVal.name] == 0.5
