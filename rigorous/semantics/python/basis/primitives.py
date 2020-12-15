# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import dataclasses as d
import typing as t

from ....core import terms
from ....data import (
    booleans,
    mappings,
    null,
    numbers,
    records,
    references,
    strings,
    tuples,
)
from ....pretty import define

from .. import factory, heap


class Implementation(t.Protocol):
    def __call__(self, arguments: t.Tuple[terms.Term, ...]) -> terms.Term:
        pass


@d.dataclass(frozen=True)
class Primitive:
    name: str
    description: str
    implementation: Implementation
    location: define.LocationInfo

    parameter_types: t.Tuple[t.Type[terms.Term], ...]
    return_type: t.Type[terms.Term]


_primitives: t.Dict[str, Primitive] = {}


def is_primitive(name: str) -> bool:
    return name in _primitives


def get_primitive(name: str) -> Primitive:
    return _primitives[name]


def get_primitives() -> t.Mapping[str, Primitive]:
    return _primitives


PrimitiveFunctionT = t.TypeVar("PrimitiveFunctionT", bound=t.Callable[..., terms.Term])


class PrimitiveDecorator(t.Protocol):
    def __call__(self, function: PrimitiveFunctionT) -> PrimitiveFunctionT:
        raise NotImplementedError()


class InvalidOperationError(Exception):
    reason: str

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def primitive(name: str) -> PrimitiveDecorator:
    def decorator(function: PrimitiveFunctionT) -> PrimitiveFunctionT:
        import inspect

        signature = inspect.signature(function)
        type_hints = t.get_type_hints(function)

        types: t.Dict[str, t.Type[terms.Term]] = {}

        for parameter in signature.parameters.values():
            typ = type_hints.get(parameter.name, terms.Term)
            assert isinstance(typ, type) and issubclass(
                typ, terms.Term
            ), f"invalid type annotation {typ} for parameter {parameter.name}"
            types[parameter.name] = typ

        def implementation(arguments: t.Tuple[terms.Term, ...]) -> terms.Term:
            if len(arguments) != len(signature.parameters):
                return factory.runtime(
                    "raise_primitive_error",
                    strings.create(
                        f"internal error: primitive {name!r} expects"
                        f" {len(signature.parameters)} arguments but"
                        f" {len(arguments)} were given"
                    ),
                )
            else:
                for parameter, argument in zip(signature.parameters, arguments):
                    if not isinstance(argument, types[parameter]):
                        return factory.runtime(
                            "raise_primitive_error",
                            strings.create(
                                f"internal error: wrong type of parameter {parameter}"
                                f" expected {types[parameter]} but got {type(argument)}"
                            ),
                        )
                try:
                    return function(*arguments)
                except InvalidOperationError as error:
                    return factory.runtime(
                        "raise_primitive_error", strings.create(error.reason),
                    )

        _primitives[name] = Primitive(
            name,
            function.__doc__ or "",
            implementation,
            define.get_location_info(),
            tuple(types[parameter] for parameter in signature.parameters),
            type_hints["return"],
        )

        return function

    return decorator


@terms.function_operator
def apply(name: strings.String, arguments: tuples.Tuple) -> terms.Term:
    try:
        primitive = _primitives[name.value]
    except KeyError:
        return factory.runtime(
            "raise_primitive_error",
            strings.create(f"no primitive with name {name.value!r}"),
        )
    else:
        return primitive.implementation(arguments.components)


# region: Reference Primitives


_NAMED_REFERENCE_IDS: t.Dict[str, int] = {}


@primitive("reference_id")
def primitive_reference_id(obj: references.Reference) -> numbers.Number:
    r"""
    Returns a unique numeric identifier for the given reference.

    We use this primitive to implement Python's \verb!id! function.
    """
    if obj.name is None:
        assert obj.address is not None
        assert obj.address <= 1 << 32 - 1
        return numbers.create((1 << 32) | obj.address)
    else:
        try:
            identifier = _NAMED_REFERENCE_IDS[obj.name]
        except KeyError:
            identifier = _NAMED_REFERENCE_IDS[obj.name] = len(_NAMED_REFERENCE_IDS)
        return numbers.create(identifier)


@primitive("reference_hash")
def primitive_reference_hash(obj: references.Reference) -> numbers.Number:
    r"""
    Returns a hash for the given reference.

    In Python most objects are hashable based on their identity. This function
    returns a hash value based on the identity of the reference.
    """
    return numbers.create(hash(obj))


# endregion


# region: Number Primitives


@primitive("number_add")
def primitive_number_add(left: numbers.Number, right: numbers.Number) -> numbers.Number:
    """
    Returns the sum of both numbers.
    """
    return numbers.create(left.value + right.value)


@primitive("number_sub")
def primitive_number_sub(left: numbers.Number, right: numbers.Number) -> numbers.Number:
    """
    Returns the difference of both numbers.
    """
    return numbers.create(left.value - right.value)


@primitive("number_mul")
def primitive_number_mul(left: numbers.Number, right: numbers.Number) -> numbers.Number:
    """
    Returns the product of both numbers.
    """
    return numbers.create(left.value * right.value)


@primitive("number_str")
def primitive_number_str(number: numbers.Number) -> strings.String:
    """
    Converts a number into a primitive string.
    """
    return strings.create(str(number.value))


@primitive("number_neg")
def primitive_number_neg(number: numbers.Number) -> numbers.Number:
    """
    Flips the sign of the number.
    """
    return numbers.create(-number.value)


@primitive("number_hash")
def primitive_number_hash(number: numbers.Number) -> numbers.Number:
    """
    Computes the hash of the number.

    Numbers are hashed in Python by treating them as rationals. This
    allows hashing numbers independent of their representation, e.g.,
    the float $1.0$ and the integer $1$ have the same hash.
    """
    return numbers.create(hash(number.value))


# endregion


# region: Record Primitives


@primitive("make_record")
def primitive_make_record(fields: tuples.Tuple) -> records.Record:
    """
    Turns a vector of pairs $(s, t)$ into a record.

    The first component of each pair is required to be a string
    representing a field name. The resulting record then maps
    those fields to the respective terms given by the second
    component of each pair.
    """
    record_fields: t.Dict[str, terms.Term] = {}
    for field in fields.components:
        assert isinstance(field, tuples.Tuple)
        assert len(field.components) == 2
        name, value = field.components
        assert isinstance(name, strings.String)
        record_fields[name.value] = value
    return records.create(**record_fields)


@primitive("record_get")
def primitive_record_get(record: records.Record, field: strings.String) -> terms.Term:
    """
    Retrives the value of the given field from a record.
    """
    if field.value in record.fields:
        return record.fields[field.value]
    else:
        raise InvalidOperationError(
            f"record {record} does not have field {field.value!r}"
        )


@primitive("record_get_default")
def primitive_record_get_default(
    record: records.Record, field: strings.String, default: terms.Term
) -> terms.Term:
    """
    Retrives the value of the given field from a record and returns the
    default value in case no such field does exist.
    """
    return record.fields.get(field.value, default)


@primitive("record_set")
def primitive_record_set(
    record: records.Record, field: strings.String, value: terms.Term
) -> records.Record:
    """
    Sets the specified field to the provided term.

    Returns a record that is identical to the first argument except that
    the field represented by the second argument is set to the value
    provided as third argument.
    """
    return record.setfield(field.value, value)


# endregion


# region: Sequence Primitives


@primitive("sequence_length")
def primitive_sequence_length(sequence: tuples.Tuple) -> numbers.Number:
    """
    Returns the length of the vector.
    """
    return numbers.create(len(sequence.components))


@primitive("sequence_get")
def primitive_sequence_get(
    sequence: tuples.Tuple, index: numbers.Integer
) -> terms.Term:
    """
    Retrieves the element at the provided index of the vector.
    """
    try:
        return sequence.components[index.value]
    except IndexError:
        raise InvalidOperationError("index out of bounds")


@primitive("sequence_set")
def primitive_sequence_set(
    sequence: tuples.Tuple, index: numbers.Integer, value: terms.Term
) -> tuples.Tuple:
    """
    Sets the value at the specified index of the vector.
    """
    try:
        components = list(sequence.components)
        components[index.value] = value
        return tuples.Tuple(tuple(components))
    except IndexError:
        raise InvalidOperationError("index out of bounds")


@primitive("sequence_push")
def primitive_sequence_push(
    sequence: tuples.Tuple, element: terms.Term
) -> tuples.Tuple:
    """
    Appends a value to the right side of the vector.
    """
    return tuples.Tuple(sequence.components + (element,))


@primitive("sequence_push_left")
def primitive_sequence_push_left(
    sequence: tuples.Tuple, element: terms.Term
) -> tuples.Tuple:
    """
    Appends a value to the left side of the vector.
    """
    return tuples.Tuple((element,) + sequence.components)


@primitive("sequence_pop")
def primitive_sequence_pop(sequence: tuples.Tuple) -> tuples.Tuple:
    """
    Removes a value from the right side of the vector.
    """
    return tuples.Tuple(sequence.components[:-1])


@primitive("sequence_pop_left")
def primitive_sequence_pop_left(sequence: tuples.Tuple) -> tuples.Tuple:
    """
    Removes a value from the left side of the vector.
    """
    return tuples.Tuple(sequence.components[1:])


@primitive("sequence_concat")
def primitive_sequence_concat(
    sequence: tuples.Tuple, other: tuples.Tuple
) -> tuples.Tuple:
    """
    Concatenates both vectors.
    """
    return tuples.Tuple(sequence.components + other.components)


@primitive("sequence_delete")
def primitive_sequence_delete(
    sequence: tuples.Tuple, index: numbers.Integer
) -> tuples.Tuple:
    """
    Removes the value at the specified index from the vector.
    """
    components = list(sequence.components)
    del components[index.value]
    return tuples.Tuple(tuple(components))


@primitive("sequence_slice")
def primitive_sequence_slice(
    sequence: tuples.Tuple, start: numbers.Integer, end: numbers.Integer
) -> tuples.Tuple:
    r"""
    Returns the specified slice of the vector.
    """
    return tuples.Tuple(sequence.components[start.value : end.value])


# endregion


# region: String Primitives


@primitive("string_hash")
def primitive_string_hash(string: strings.String) -> numbers.Number:
    r"""
    Returns the hash for the string.

    String hashing in Python is randomized. The value returned by this
    primitive depends on the environment variable \verb!PYTHONHASHSEED!.
    """
    return numbers.create(hash(string.value))


@primitive("string_equals")
def primitive_string_equals(
    left: strings.String, right: strings.String
) -> booleans.Boolean:
    """
    Checks equality of two strings.
    """
    return booleans.create(left.value == right.value)


@primitive("string_join")
def primitive_string_join(
    sep: strings.String, elements: tuples.Tuple
) -> strings.String:
    """
    Joins a vector of strings with the provided seperator.
    """
    chunks: t.List[str] = []
    for element in elements.components:
        if not isinstance(element, strings.String):
            raise InvalidOperationError(f"expected string but found {type(element)}")
        chunks.append(element.value)
    return strings.create(sep.value.join(chunks))


@primitive("string_concat")
def primitive_string_concat(
    left: strings.String, right: strings.String
) -> strings.String:
    """
    Concatenates two strings.
    """
    return strings.create(left.value + right.value)


@primitive("string_rpartition")
def primitive_string_rpartition(
    string: strings.String, seperator: strings.String
) -> tuples.Tuple:
    """
    Partitions a string from the right.
    """
    return tuples.create(*map(strings.create, string.value.rpartition(seperator.value)))


@primitive("string_repr")
def primitive_string_repr(string: strings.String) -> strings.String:
    r"""
    Returns the Python \verb!repr! of the string.
    """
    return strings.create(repr(string.value))


@primitive("string_length")
def primitive_length(string: strings.String) -> numbers.Number:
    """
    Returns the length of the string.
    """
    return numbers.create(len(string.value))


# endregion


# region: Mapping Primitives


@primitive("mapping_get")
def primitive_mapping_get(mapping: mappings.Mapping, key: terms.Term) -> terms.Term:
    """
    Retrieves a value from the mapping using the provided key.
    """
    return mapping.entries[key]


@primitive("mapping_get_default")
def primitive_mapping_get_default(
    mapping: mappings.Mapping, key: terms.Term, default: terms.Term
) -> terms.Term:
    """
    Retrives a value from the mapping using the provided key. In case no such
    value exists, the provided default value is returned.
    """
    return mapping.entries.get(key, default)


@primitive("mapping_set")
def primitive_mapping_set(
    mapping: mappings.Mapping, key: terms.Term, value: terms.Term
) -> mappings.Mapping:
    """
    Puts a key-value pair into the mapping.
    """
    return mappings.Mapping(mapping.entries.set(key, value))


@primitive("mapping_contains")
def primitive_mapping_contains(
    mapping: mappings.Mapping, key: terms.Term
) -> booleans.Boolean:
    """
    Checks whether the mapping contains the provided key.
    """
    return booleans.create(key in mapping.entries)


@primitive("mapping_delete")
def primitive_mapping_delete(
    mapping: mappings.Mapping, key: terms.Term
) -> mappings.Mapping:
    """
    Deletes a key from the mapping.
    """
    return mapping.delitem(key)


@primitive("mapping_update")
def primitive_mapping_update(
    mapping: mappings.Mapping, other: mappings.Mapping
) -> mappings.Mapping:
    """
    Updates a mapping with the key-value pairs of the other mapping.
    """
    return mappings.Mapping(mapping.entries.update(other.entries))


@primitive("mapping_keys")
def primitive_mapping_keys(mapping: mappings.Mapping) -> tuples.Tuple:
    """
    Returns the sequence of keys of the mapping.
    """
    return tuples.create(*mapping.entries)


@primitive("mapping_size")
def primitive_mapping_size(mapping: mappings.Mapping) -> numbers.Number:
    """
    Returns the number of entries of the mapping.
    """
    return numbers.create(len(mapping.entries))


# endregion


# region: Other Primitives


@primitive("send_value")
def primitive_send_value(frame: records.Record, value: terms.Term) -> terms.Term:
    r"""
    Constructs a $\tVerbSym{send\_value}$ term for sending a value
    to a generator. The first argument is the frame descriptor to
    resume execution from and the second is the value to send.
    """
    return factory.create_send_value(frame, value)


@primitive("send_throw")
def primitive_send_throw(frame: records.Record, value: terms.Term) -> terms.Term:
    r"""
    Constructs a $\tVerbSym{send\_throw}$ term for throwing an
    exception into a generator. The first argument is the frame
    descriptor to resume execution from and the second is the
    exception to throw.
    """
    return factory.create_send_throw(frame, value)


@primitive("make_frame")
def primitive_make_frame(
    code: records.Record, namespace: mappings.Mapping
) -> records.Record:
    """
    Creates a frame descriptor from the given code object and namespace.
    """
    return records.create(
        cls=heap.TYPE_CODE,
        dict=null.NULL,
        locals=namespace,
        body=code.getfield("body"),
    )


# endregion
