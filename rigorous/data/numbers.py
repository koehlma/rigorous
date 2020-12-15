# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import dataclasses as d
import typing as t

import abc

from ..core import terms


class Number(terms.Value, abc.ABC):
    value: t.Union[int, float]


@d.dataclass(frozen=True)
class Integer(Number):
    value: int


@d.dataclass(frozen=True)
class Float(Number):
    value: float


@terms.function_operator
def add(left: Number, right: Number) -> Number:
    return create(left.value + right.value)


@terms.function_operator
def sub(left: Number, right: Number) -> Number:
    return create(left.value - right.value)


@terms.function_operator
def mul(left: Number, right: Number) -> Number:
    return create(left.value * right.value)


@terms.function_operator
def real_div(left: Number, right: Number) -> Number:
    return create(left.value / right.value)


@terms.function_operator
def floor_div(left: Number, right: Number) -> Number:
    return create(left.value // right.value)


@terms.function_operator
def power(left: Number, right: Number) -> Number:
    return create(left.value ** right.value)


@terms.function_operator
def mod(left: Number, right: Number) -> Number:
    return create(left.value % right.value)


@terms.function_operator
def absolute(operand: Number) -> Number:
    return create(abs(operand.value))


@terms.function_operator
def neg(operand: Number) -> Number:
    return create(-operand.value)


@terms.function_operator
def shift_left(left: Integer, right: Integer) -> Integer:
    return Integer(left.value >> right.value)


@terms.function_operator
def shift_right(left: Integer, right: Integer) -> Integer:
    return Integer(left.value >> right.value)


@terms.function_operator
def bitwise_and(left: Integer, right: Integer) -> Integer:
    return Integer(left.value & right.value)


@terms.function_operator
def bitwise_or(left: Integer, right: Integer) -> Integer:
    return Integer(left.value | right.value)


@terms.function_operator
def bitwise_xor(left: Integer, right: Integer) -> Integer:
    return Integer(left.value ^ right.value)


def create(value: t.Union[int, float]) -> Number:
    if isinstance(value, int):
        return Integer(value)
    else:
        return Float(value)
