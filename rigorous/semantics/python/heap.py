# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import dataclasses as d
import typing as t

import immutables

from ...core import terms
from ...data import (
    booleans,
    mappings,
    numbers,
    records,
    references,
    strings,
    tuples,
)


# Prepare some references for builtins. The objects descriptors stored at
# these references are created later as part of the initialization process.
TYPE_OBJECT = references.Reference("object")
TYPE_TYPE = references.Reference("type")

TYPE_STR = references.Reference("str")
TYPE_INT = references.Reference("int")
TYPE_FLOAT = references.Reference("float")
TYPE_DICT = references.Reference("dict")
TYPE_TUPLE = references.Reference("tuple")

TYPE_CODE = references.Reference("code")
TYPE_FUNCTION = references.Reference("function")

TYPE_MAPPING_PROXY = references.Reference("mappingproxy")

TYPE_NOT_IMPLEMENTED = references.Reference("NotImplementedType")
NOT_IMPLEMENTED = references.Reference("NotImplemented")

TYPE_ELLIPSIS = references.Reference("ellipsis")
ELLIPSIS = references.Reference("Ellipsis")

TYPE_NONE = references.Reference("NoneType")
NONE = references.Reference("None")

TYPE_BOOL = references.Reference("bool")
TRUE = references.Reference("True")
FALSE = references.Reference("False")


SENTINEL = references.Reference("SENTINEL")


BUILTIN_GLOBALS = references.Reference("BUILTIN_GLOBALS")


@d.dataclass(frozen=True)
class ObjectProxy:
    builder: Builder
    reference: references.Reference

    @property
    def _descriptor(self) -> records.Record:
        descriptor = self.builder.memory[self.reference]
        assert isinstance(
            descriptor, records.Record
        ), "object descriptor should be a record"
        return descriptor

    @property
    def attrs(self) -> MappingProxy:
        attrs = self._descriptor.getfield("dict")
        assert isinstance(attrs, references.Reference)
        assert attrs is not NONE
        return MappingProxy(self.builder, attrs)


class TypeProxy(ObjectProxy):
    @property
    def name(self) -> str:
        name = self._descriptor.getfield("name")
        assert isinstance(name, strings.String)
        return name.value

    @property
    def mro(self) -> t.Sequence[TypeProxy]:
        mro = self._descriptor.getfield("mro")
        assert isinstance(mro, tuples.Tuple)
        return tuple(
            self.builder.get_type_proxy(reference)  # type: ignore
            for reference in mro.components
        )

    @property
    def bases(self) -> t.Sequence[TypeProxy]:
        bases = self._descriptor.getfield("bases")
        assert isinstance(bases, tuples.Tuple)
        return tuple(
            self.builder.get_type_proxy(reference)  # type: ignore
            for reference in bases.components
        )

    def __repr__(self) -> str:
        return f"<TypeProxy for {self.name!r}>"

    def set_slot(self, slot: str, func: references.Reference) -> None:
        # slots = self._descriptor.getfield("slots")
        # assert isinstance(slots, mappings.Mapping)
        # slots = slots.setitem(strings.create(slot), func)
        # self.builder.store(self.reference, self._descriptor.setfield("slots", slots))
        self.attrs.setitem(strings.create(slot), func)


class MappingProxy(ObjectProxy):
    def setitem(self, key: terms.Term, value: terms.Term) -> None:
        mapping = self._descriptor.getfield("value")
        assert isinstance(mapping, mappings.Mapping)
        self.builder.store(
            self.reference,
            self._descriptor.setfield("value", mapping.setitem(key, value)),
        )


def compute_mro(cls: TypeProxy, bases: t.Sequence[TypeProxy]) -> t.Sequence[TypeProxy]:
    pending = [base.mro for base in bases]
    result = [cls]
    while pending:
        for mro in pending:
            head = mro[0]
            good = all(head not in other_mro[1:] for other_mro in pending)
            if good:
                result.append(head)
                pending = [
                    [cls for cls in other_mro if cls != head]
                    for other_mro in pending
                    if head not in other_mro or len(other_mro) > 1
                ]
                break
        else:
            raise Exception(f"unable to linearize class hierarchy for {cls.name}")
    return result


Ref = t.Optional[t.Union[str, references.Reference]]


class Builder:
    memory: t.Dict[references.Reference, terms.Term]

    next_address: int

    def __init__(
        self,
        *,
        _memory: t.Optional[t.Dict[references.Reference, terms.Term]] = None,
        _next_address: t.Optional[int] = None,
    ) -> None:
        self.memory = _memory or {}
        self.next_address = _next_address or 0
        if _memory is None:
            self._initialize()

    @classmethod
    def from_heap(cls, heap: references.Heap) -> Builder:
        return cls(
            _memory=dict(heap.entries),  # type: ignore
            _next_address=heap.next_address,
        )

    def _initialize(self) -> None:
        self.new_type("object", bases=(), mro=(), ref=TYPE_OBJECT)
        self.new_type("type", ref=TYPE_TYPE)

        self.new_type("str", ref=TYPE_STR)
        self.new_type("int", ref=TYPE_INT)
        self.new_type("float", ref=TYPE_FLOAT)
        self.new_type("dict", ref=TYPE_DICT)
        self.new_type("tuple", ref=TYPE_TUPLE)

        self.new_type("code", ref=TYPE_CODE)
        self.new_type("function", ref=TYPE_FUNCTION)

        self.new_type("mappingproxy", ref=TYPE_MAPPING_PROXY)

        self.new_type("NotImplementedType", ref=TYPE_NOT_IMPLEMENTED, is_sealed=True)
        self.new_object(cls=TYPE_NOT_IMPLEMENTED, ref=NOT_IMPLEMENTED)

        self.new_type("Ellipsis", ref=TYPE_ELLIPSIS, is_sealed=True)
        self.new_object(cls=TYPE_ELLIPSIS, ref=ELLIPSIS)

        self.new_type("NoneType", ref=TYPE_NONE, is_sealed=True)
        self.new_object(cls=TYPE_NONE, ref=NONE)

        self.new_type(
            "bool",
            bases=(TYPE_INT,),
            mro=(TYPE_INT, TYPE_OBJECT),
            ref=TYPE_BOOL,
            is_sealed=True,
        )
        self.new_int(1, cls=TYPE_BOOL, ref=TRUE)
        self.new_int(0, cls=TYPE_BOOL, ref=FALSE)

        self.new_dict(ref=BUILTIN_GLOBALS)

    def store(self, reference: references.Reference, value: terms.Term) -> None:
        self.memory[reference] = value

    def get_type_proxy(self, reference: references.Reference) -> TypeProxy:
        return TypeProxy(self, reference)

    def is_defined(self, reference: references.Reference) -> bool:
        return reference in self.memory

    @property
    def heap(self) -> references.Heap:
        return references.Heap(
            immutables.Map(t.cast(t.Mapping[terms.Term, terms.Term], self.memory)),
            self.next_address,
        )

    def new_reference(self, name: t.Optional[str] = None) -> references.Reference:
        address: t.Optional[int]
        if name is None:
            address = self.next_address
            self.next_address += 1
        else:
            address = None
        reference = references.Reference(name=name, address=address)
        return reference

    def clone(self) -> Builder:
        return Builder(_memory=dict(self.memory), _next_address=self.next_address)

    def _reference(self, ref: Ref) -> references.Reference:
        if isinstance(ref, references.Reference):
            return ref
        else:
            return self.new_reference(name=ref)

    def new_object(
        self,
        cls: references.Reference = TYPE_OBJECT,
        attrs: t.Optional[terms.Term] = None,
        ref: Ref = None,
        **fields: terms.Term,
    ) -> references.Reference:
        reference = self._reference(ref)
        self.memory[reference] = records.create(
            cls=cls, dict=attrs or self.new_mapping_proxy(), **fields
        )
        return reference

    def new_type(
        self,
        name: str,
        cls: references.Reference = TYPE_TYPE,
        bases: t.Sequence[references.Reference] = (TYPE_OBJECT,),
        mro: t.Optional[t.Sequence[references.Reference]] = None,
        ref: Ref = None,
        is_sealed: bool = False,
        is_builtin: bool = True,
        layout: t.Optional[references.Reference] = None,
    ) -> references.Reference:
        reference = self._reference(ref)
        if bases == (TYPE_OBJECT,) and mro is None:
            mro_tuple = tuples.create(reference, TYPE_OBJECT)
        elif mro is not None:
            mro_tuple = tuples.create(reference, *mro)
        else:
            mro_tuple = tuples.create(
                *(
                    typ.reference
                    for typ in compute_mro(
                        self.get_type_proxy(reference),
                        tuple(self.get_type_proxy(base) for base in bases),
                    )
                )
            )
        return self.new_object(
            cls=cls,
            ref=reference,
            name=strings.create(name),
            bases=tuples.create(*bases),
            mro=mro_tuple,
            slots=mappings.EMPTY,
            is_sealed=booleans.create(is_sealed),
            is_builtin=booleans.create(is_builtin),
            layout=layout or reference,
        )

    def new_int(
        self,
        value: int,
        *,
        cls: references.Reference = TYPE_INT,
        ref: t.Optional[t.Union[str, references.Reference]] = None,
    ) -> references.Reference:
        return self.new_object(
            cls=cls, attrs=NONE, value=numbers.create(value), ref=ref
        )

    def new_float(self, value: float) -> references.Reference:
        return self.new_object(cls=TYPE_FLOAT, attrs=NONE, value=numbers.create(value))

    def new_string(self, value: str) -> references.Reference:
        return self.new_object(cls=TYPE_STR, attrs=NONE, value=strings.create(value))

    def new_tuple(self, *components: references.Reference) -> references.Reference:
        return self.new_object(
            cls=TYPE_TUPLE, attrs=NONE, value=tuples.create(*components)
        )

    def new_dict(
        self, ref: t.Optional[t.Union[str, references.Reference]] = None,
    ) -> references.Reference:
        return self.new_object(
            cls=TYPE_DICT, attrs=NONE, value=tuples.create(), ref=ref
        )

    def new_code(
        self,
        body: terms.Term,
        *,
        name: str = "<module>",
        filename: str = "<string>",
        cells: t.Tuple[str, ...] = (),
        signature: terms.Term = tuples.EMPTY,
        doc: terms.Term = NONE,
        is_generator: bool = False,
    ) -> references.Reference:
        return self.new_object(
            cls=TYPE_CODE,
            name=strings.create(name),
            filename=strings.create(filename),
            cells=tuples.create(*map(strings.create, cells)),
            signature=signature,
            doc=doc,
            body=body,
            is_generator=booleans.create(is_generator),
        )

    def new_function(
        self,
        code: references.Reference,
        name: str,
        global_namespace: references.Reference,
        *,
        defaults: terms.Term = mappings.EMPTY,
        cells: terms.Term = mappings.EMPTY,
        ref: Ref = None,
    ) -> references.Reference:
        return self.new_object(
            cls=TYPE_FUNCTION,
            name=strings.create(name),
            code=code,
            qualname=NONE,
            doc=strings.create(""),
            globals=global_namespace,
            module=NONE,
            defaults=defaults,
            cells=cells,
            ref=ref,
        )

    def new_mapping_proxy(
        self, mapping: mappings.Mapping = mappings.EMPTY
    ) -> references.Reference:
        return self.new_object(cls=TYPE_MAPPING_PROXY, attrs=NONE, value=mapping)
