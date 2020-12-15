# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import dataclasses as d
import typing as t

from ..core import terms

from . import numbers


@d.dataclass(frozen=True)
class Tuple(terms.Value):
    components: t.Tuple[terms.Term, ...] = ()


def create(*components: terms.Term) -> Tuple:
    return Tuple(components)


EMPTY = Tuple()


@terms.function_operator
def project_operator(this: Tuple, index: numbers.Integer) -> t.Optional[terms.Term]:
    try:
        return this.components[index.value]
    except IndexError:
        return None


def project(this: terms.Term, index: t.Union[int, terms.Term]) -> terms.Term:
    return project_operator(
        this, numbers.Integer(index) if isinstance(index, int) else index
    )


@terms.function_operator
def length(this: Tuple) -> numbers.Number:
    return numbers.create(len(this.components))


@terms.function_operator
def push(this: Tuple, value: terms.Term) -> Tuple:
    return Tuple(this.components + (value,))


@terms.function_operator
def push_left(this: Tuple, value: terms.Term) -> Tuple:
    return Tuple((value,) + this.components)


@terms.function_operator
def pop(this: Tuple) -> t.Optional[Tuple]:
    if not this.components:
        return None
    return Tuple(this.components[:-1])


@terms.function_operator
def pop_left(this: Tuple) -> t.Optional[Tuple]:
    if not this.components:
        return None
    return Tuple(this.components[1:])


@terms.function_operator
def concat(left: Tuple, right: Tuple) -> Tuple:
    return Tuple(left.components + right.components)


@terms.operator
def construct(arguments: terms.Arguments) -> t.Optional[terms.Term]:
    return Tuple(arguments)
