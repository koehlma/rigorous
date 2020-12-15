# flake8: noqa
# type: ignore


class X(int):
    def __new__(cls):
        return 5

    def __init__(self):
        assert False


X()
