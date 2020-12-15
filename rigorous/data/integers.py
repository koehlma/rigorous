# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import dataclasses as d
import typing as t

from ..core import terms


@d.dataclass(frozen=True)
class Integer(terms.Value):
    value: int


@terms.operator
@terms.check_arity(2)
def add(arguments: terms.Arguments) -> t.Optional[terms.Term]:
    x, y = arguments
    if isinstance(x, Integer) and isinstance(y, Integer):
        return Integer(x.value + y.value)
    return None


@terms.operator
@terms.check_arity(2)
def sub(arguments: terms.Arguments) -> t.Optional[terms.Term]:
    x, y = arguments
    if isinstance(x, Integer) and isinstance(y, Integer):
        return Integer(x.value - y.value)
    return None


def integer(value: int) -> Integer:
    return Integer(value)
