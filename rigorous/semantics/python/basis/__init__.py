# -*- coding: utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import typing as t

from ....data import references

from ..syntax import blocks, parser

from .. import heap

from .source import builtins_source, runtime_source

from . import macros, primitives


builtin_constants: t.Dict[str, references.Reference] = {
    "object": heap.TYPE_OBJECT,
    "type": heap.TYPE_TYPE,
    "str": heap.TYPE_STR,
    "int": heap.TYPE_INT,
    "float": heap.TYPE_FLOAT,
    "dict": heap.TYPE_DICT,
    "tuple": heap.TYPE_TUPLE,
    "bool": heap.TYPE_BOOL,
    "NotImplemented": heap.NOT_IMPLEMENTED,
    "Ellipsis": heap.ELLIPSIS,
}

runtime_constants: t.Dict[str, references.Reference] = {
    "code": heap.TYPE_CODE,
    "function": heap.TYPE_FUNCTION,
    "mappingproxy": heap.TYPE_MAPPING_PROXY,
    "NotImplementedType": heap.TYPE_NOT_IMPLEMENTED,
    "ellipsis": heap.TYPE_ELLIPSIS,
    "NoneType": heap.TYPE_NONE,
    "SENTINEL": heap.SENTINEL,
}

runtime_functions: t.Set[str] = set()


builtins_module = parser.parse_module(builtins_source, mode=parser.Mode.PRIMITIVE)
runtime_module = parser.parse_module(runtime_source, mode=parser.Mode.PRIMITIVE)


def lookup(identifier: str) -> references.Reference:
    if identifier in runtime_constants:
        return runtime_constants[identifier]
    else:
        assert identifier in builtin_constants
        return builtin_constants[identifier]


def _forward_declare() -> None:
    for child in builtins_module.children:
        if isinstance(child, blocks.FunctionDefinition):
            assert child.identifier not in builtin_constants
            reference = references.Reference(f"builtin_{child.identifier}")
            builtin_constants[child.identifier] = reference
        elif isinstance(child, blocks.ClassDefinition):
            if child.identifier not in builtin_constants:
                reference = references.Reference(f"builtin_{child.identifier}")
                builtin_constants[child.identifier] = reference
    for child in runtime_module.children:
        if isinstance(child, blocks.FunctionDefinition):
            assert child.identifier not in runtime_functions
            runtime_functions.add(child.identifier)
        elif isinstance(child, blocks.ClassDefinition):
            if (
                child.identifier not in runtime_constants
                and child.identifier not in builtin_constants
            ):
                reference = references.Reference(f"runtime_{child.identifier}")
                runtime_constants[child.identifier] = reference

    runtime_constants["BUILTINS"] = references.Reference("BUILTINS")


_forward_declare()


__all__ = [
    "macros",
    "primitives",
    "builtin_constants",
    "runtime_constants",
    "runtime_functions",
    "builtins_module",
    "runtime_module",
]
