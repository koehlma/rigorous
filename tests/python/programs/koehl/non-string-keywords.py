# flake8: noqa
# type: ignore


def f(**kwargs):
    pass


try:
    f(**{3: 5})
    assert False
except TypeError:
    x = 5
assert x == 5
