# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import dataclasses as d
import typing as t

from ...core import terms
from ...data import mappings, records, strings, tuples


@d.dataclass(frozen=True)
class RuntimeFunction:
    name: str
    parameters: t.Tuple[str, ...]
    body: terms.Term
    docstring: t.Optional[str] = None
    lineno: t.Optional[int] = None


_runtime_functions: t.Dict[str, RuntimeFunction] = {}

_declared: t.Set[str] = set()


def get_runtime_functions() -> t.Mapping[str, RuntimeFunction]:
    return _runtime_functions


def declare_runtime_function(name: str) -> None:
    _declared.add(name)


def is_runtime_function(name: str) -> bool:
    return name in _declared


def define_runtime_function(
    name: str,
    parameters: t.Tuple[str, ...],
    body: terms.Term,
    *,
    docstring: t.Optional[str] = None,
    lineno: t.Optional[int] = None,
) -> RuntimeFunction:
    function = RuntimeFunction(name, parameters, body, docstring, lineno)
    _runtime_functions[name] = function
    return function


@terms.function_operator
def make_runtime_frame(
    name: strings.String, arguments: tuples.Tuple
) -> t.Optional[terms.Term]:
    try:
        function = _runtime_functions[name.value]
        namespace: t.Dict[terms.Term, terms.Term] = {}
        for parameter, value in zip(function.parameters, arguments.components):
            namespace[strings.create(parameter)] = value
        return records.create(locals=mappings.create(namespace), body=function.body)
    except KeyError:
        return terms.symbol(f"runtime function {name.value!r} used but not implemented")


COMPARE_FUNCTIONS = {
    "==": "cmp_eq",
    "!=": "cmp_ne",
    "<": "cmp_lt",
    "<=": "cmp_le",
    ">=": "cmp_ge",
    ">": "cmp_gt",
    "in": "cmp_in",
    "not in": "cmp_not_in",
}
