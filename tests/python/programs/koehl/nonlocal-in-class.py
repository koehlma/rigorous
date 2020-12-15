y = 1


def f():
    x = 3

    class X:
        nonlocal x
        global y
        x = 5
        y = 6

    assert x == 5


f()

assert y == 6
