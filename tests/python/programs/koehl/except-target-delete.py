# flake8: noqa
# type: ignore

x = 0
try:
    try:
        raise TypeError()
    except TypeError as e:
        try:
            raise ValueError()
        except ValueError as e:
            pass
        e
        raise AssertionError()
except NameError:
    x = 5
assert x == 5
