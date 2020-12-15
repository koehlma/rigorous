# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import dataclasses as d
import typing as t

from ..core import terms

from . import booleans, mappings


@d.dataclass(frozen=True)
class Reference(terms.Value):
    name: t.Optional[str] = None
    address: t.Optional[int] = None

    def __post_init__(self) -> None:
        assert (
            self.name is not None or self.address is not None
        ), "reference must either be named or have an address"


NULL = Reference("NULL")


@terms.function_operator
def is_reference(term: terms.Term) -> terms.Term:
    return booleans.create(isinstance(term, Reference))


@d.dataclass(frozen=True)
class Heap(mappings.Mapping):
    next_address: int = 0


@terms.function_operator
def new(heap: Heap, value: terms.Term) -> terms.Term:
    address = heap.next_address
    reference = Reference(address=address)
    return create_new_result(
        Heap(heap.entries.set(reference, value), address + 1), reference
    )


@terms.function_operator
def store(heap: Heap, reference: Reference, value: terms.Term) -> terms.Term:
    return Heap(heap.entries.set(reference, value), heap.next_address)


def create_new_result(heap: terms.Term, reference: terms.Term) -> terms.Term:
    return terms.sequence(heap, ",", reference)
