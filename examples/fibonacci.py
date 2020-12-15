# -*- coding: utf-8 -*-


def fibonacci(n: int) -> int:
    assert n >= 0, "fibonacci is undefined for negative integers"
    if n < 2:
        return n
    else:
        return fibonacci(n - 1) + fibonacci(n - 2)


print(fibonacci(4))
