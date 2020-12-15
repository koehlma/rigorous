class M(type):
    x = 5


class X:
    x = 6


class Y(X, metaclass=M):
    pass


class Z(metaclass=M):
    pass


x = 0

assert M.x == 5
assert X.x == 6
assert Y.x == 6
assert Z.x == 5
try:
    assert Z().x
except AttributeError:
    x = 42

assert x == 42
