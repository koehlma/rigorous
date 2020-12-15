class X:
    def __init__(self):
        self._x = 3

    @property
    def x(self):
        return self._x

    @x.setter
    def x(self, value):
        self._x = value

    @x.deleter
    def x(self):
        self._x = None


x = X()
assert x.x == 3
x.x = 5
assert x.x == 5
del x.x
assert x.x is None
