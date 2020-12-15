# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import typing as t

import enum


class Operator:
    symbol: str
    _method: t.Optional[str]

    def __init__(self, symbol: str, method: t.Optional[str] = None):
        self.symbol = symbol
        self._method = method

    @property
    def has_method(self) -> bool:
        return self._method is not None

    @property
    def method(self) -> str:
        assert self._method is not None
        return self._method


class UnaryOperator(Operator, enum.Enum):
    PLUS = "+", "pos"
    MINUS = "-", "neg"
    INVERT = "~", "invert"

    @property
    def slot(self) -> str:
        return f"__{self.method}__"


class BinaryOperator(Operator, enum.Enum):
    ADD = "+", "add"
    SUB = "-", "sub"
    MUL = "*", "mul"

    REAL_DIV = "/", "div"
    FLOOR_DIV = "//", "floordiv"

    MOD = "%", "mod"
    POW = "**", "pow"

    LEFT_SHIFT = ">>", "lshift"
    RIGHT_SHIFT = "<<", "rshift"

    BIT_OR = "|", "or"
    BIT_AND = "&", "and"
    BIT_XOR = "^", "xor"

    MAT_MUL = "@", "matmul"

    @property
    def left_slot(self) -> str:
        return f"__{self.method}__"

    @property
    def right_slot(self) -> str:
        return f"__r{self.method}__"


class BooleanOperator(Operator, enum.Enum):
    AND = "and"
    OR = "or"


class ComparisonOperator(Operator, enum.Enum):
    EQUAL = "==", "eq"
    NOT_EQUAL = "!=", "ne"

    LESS = "<", "lt"
    LESS_EQUAL = "<=", "le"

    GREATER = ">", "gt"
    GREATER_EQUAL = ">=", "ge"

    IN = "in"
    NOT_IN = "not in"

    IS = "is"
    IS_NOT = "is not"
