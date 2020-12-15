# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import dataclasses as d
import typing as t

import immutables

from ..core import terms


@d.dataclass(frozen=True)
class Mapping(terms.Value, t.Mapping[terms.Term, terms.Term]):
    entries: immutables.Map[terms.Term, terms.Term]

    def __getitem__(self, key: terms.Term) -> terms.Term:
        return self.entries[key]

    def __iter__(self) -> t.Iterator[terms.Term]:
        return iter(self.entries)

    def __len__(self) -> int:
        return len(self.entries)

    def setitem(self, key: terms.Term, value: terms.Term) -> Mapping:
        assert key.is_value and value.is_value
        return Mapping(self.entries.set(key, value))

    def delitem(self, key: terms.Term) -> Mapping:
        return Mapping(self.entries.delete(key))


def create(base: t.Mapping[terms.Term, terms.Term]) -> Mapping:
    assert all(key.is_value and value.is_value for key, value in base.items())
    return Mapping(immutables.Map(base))


EMPTY = create({})


@terms.function_operator
def getitem(
    mapping: Mapping, key: terms.Term, default: t.Optional[terms.Term] = None
) -> t.Optional[terms.Term]:
    try:
        return mapping.entries[key]
    except KeyError:
        return default


@terms.function_operator
def setitem(mapping: Mapping, key: terms.Term, value: terms.Term) -> terms.Term:
    return mapping.setitem(key, value)


@terms.function_operator
def delitem(mapping: Mapping, key: terms.Term) -> t.Optional[terms.Term]:
    if key in mapping.entries:
        return mapping.delitem(key)
    else:
        return mapping


@terms.operator
def construct(arguments: terms.Arguments) -> t.Optional[terms.Term]:
    if len(arguments) % 2 != 0:
        return None
    entries: t.Dict[terms.Term, terms.Term] = {}
    for key, value in zip(arguments[::2], arguments[1::2]):
        entries[key] = value
    return Mapping(immutables.Map(entries))
