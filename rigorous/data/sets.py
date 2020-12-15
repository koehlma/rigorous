# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import dataclasses as d
import typing as t

from ..core import terms

from . import booleans


@d.dataclass(frozen=True)
class Set(terms.Value):
    members: t.FrozenSet[terms.Term]


def create(base: t.AbstractSet[terms.Term]) -> Set:
    assert all(element.is_value for element in base)
    return Set(frozenset(base))


@terms.function_operator
def contains(this: Set, value: terms.Term) -> booleans.Boolean:
    return booleans.create(value in this.members)


@terms.function_operator
def not_contains(this: Set, value: terms.Term) -> booleans.Boolean:
    return booleans.create(value not in this.members)


@terms.function_operator
def add(this: Set, value: terms.Term) -> Set:
    return Set(this.members | {value})


@terms.function_operator
def remove(this: Set, value: terms.Term) -> Set:
    return Set(this.members - {value})


@terms.function_operator
def union(left: Set, right: Set) -> Set:
    return Set(left.members | right.members)


@terms.function_operator
def intersection(left: Set, right: Set) -> Set:
    return Set(left.members & right.members)


@terms.function_operator
def difference(left: Set, right: Set) -> Set:
    return Set(left.members - right.members)


@terms.function_operator
def is_subset(left: Set, right: Set) -> booleans.Boolean:
    return booleans.create(left.members <= right.members)


@terms.function_operator
def is_strict_subset(left: Set, right: Set) -> booleans.Boolean:
    return booleans.create(left.members < right.members)


@terms.function_operator
def is_superset(left: Set, right: Set) -> booleans.Boolean:
    return booleans.create(left.members >= right.members)


@terms.function_operator
def is_strict_superset(left: Set, right: Set) -> booleans.Boolean:
    return booleans.create(left.members > right.members)


@terms.function_operator
def are_disjoint(left: Set, right: Set) -> booleans.Boolean:
    return booleans.create(left.members.isdisjoint(right.members))
