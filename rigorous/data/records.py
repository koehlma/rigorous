# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import dataclasses as d
import typing as t

import immutables

from ..core import terms

from . import strings, tuples


@d.dataclass(frozen=True)
class Record(terms.Value):
    fields: immutables.Map[str, terms.Term]

    def getfield(self, name: str) -> terms.Term:
        return self.fields[name]

    def setfield(self, name: str, value: terms.Term) -> Record:
        return Record(self.fields.set(name, value))


def create(**fields: terms.Term) -> Record:
    return Record(immutables.Map(fields))


EMPTY = create()


@terms.function_operator
def getfield_operator(record: Record, field: strings.String) -> t.Optional[terms.Term]:
    try:
        return record.fields[field.value]
    except KeyError:
        return None


def getfield(record: terms.Term, field: t.Union[str, terms.Term]) -> terms.Term:
    return getfield_operator(
        record, strings.create(field) if isinstance(field, str) else field
    )


@terms.function_operator
def setfield_operator(
    record: Record, field: strings.String, value: terms.Term
) -> terms.Term:
    return Record(record.fields.set(field.value, value))


def setfield(
    record: terms.Term, field: t.Union[str, terms.Term], value: terms.Term
) -> terms.Term:
    return setfield_operator(
        record, strings.create(field) if isinstance(field, str) else field, value,
    )


@terms.operator
def construct(arguments: terms.Arguments) -> t.Optional[terms.Term]:
    if len(arguments) % 2 != 0:
        return None
    fields: t.Dict[str, terms.Term] = {}
    for field, value in zip(arguments[::2], arguments[1::2]):
        if not isinstance(field, strings.String):
            return None
        fields[field.value] = value
    return Record(immutables.Map(fields))


@terms.function_operator
def add(this: Record, item: tuples.Tuple) -> t.Optional[terms.Term]:
    assert len(item.components) == 2
    field, value = item.components
    assert isinstance(field, strings.String)
    return this.setfield(field.value, value)
