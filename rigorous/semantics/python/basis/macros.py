# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import typing as t

from ....core import terms
from ....data import mappings, numbers, references, strings, tuples

from .. import basis, factory, heap, sugar

from ..syntax import operators, tree

if t.TYPE_CHECKING:
    from ..translator import Translator


# XXX: this is not optimal, however, there seems to be no better way
Macro = t.Callable[..., terms.Term]

MacroT = t.TypeVar("MacroT", bound=Macro)


class MacroDecorator(t.Protocol):
    def __call__(self, macro: MacroT) -> MacroT:
        raise NotImplementedError()


_macros: t.Dict[str, Macro] = {}


def is_macro(name: str) -> bool:
    return name in _macros


def get_macro(name: str) -> Macro:
    assert name in _macros, f"no macro with name {name!r}"
    return _macros[name]


def get_macros() -> t.Mapping[str, Macro]:
    return _macros


def macro(name: str) -> MacroDecorator:
    def decorator(macro: MacroT) -> MacroT:
        assert name not in _macros, f"macro {name!r} has already been defined"
        _macros[name] = macro
        return macro

    return decorator


# region: Object Macros


@macro("GET_CLS_SLOT")
def macro_get_cls_slot(
    translator: Translator, obj: tree.Expression, slot: tree.String
) -> terms.Term:
    """
    Retrieves a dunder method from the provided class.
    """
    return factory.runtime(
        "get_cls_slot",
        translator.translate_expression(obj),
        strings.create(slot.value),
    )


@macro("GET_SLOT")
def macro_get_slot(
    translator: Translator, obj: tree.Expression, slot: tree.String
) -> terms.Term:
    """
    Retrieves a dunder method from the provided object.
    """
    return factory.runtime(
        "get_cls_slot",
        factory.apply(
            "record_get",
            factory.create_mem_load(translator.translate_expression(obj)),
            strings.create("cls"),
        ),
        strings.create(slot.value),
    )


@macro("CALL_SLOT")
def macro_call_slot(
    translator: Translator,
    obj: tree.Expression,
    slot: tree.String,
    *arguments: tree.Expression,
) -> terms.Term:
    """
    Calls the specified dunder method on the provided object.
    """
    positional_arguments = [translator.translate_expression(obj)]
    positional_arguments.extend(
        translator.translate_expression(argument) for argument in arguments
    )
    return sugar.create_call(
        factory.create_binary(
            factory.runtime(
                "get_cls_slot",
                factory.apply(
                    "record_get",
                    factory.create_mem_load(translator.translate_expression(obj)),
                    strings.create("cls"),
                ),
                strings.create(slot.value),
            ),
            operators.BooleanOperator.OR,
            sugar.create_raise(basis.lookup("TypeError")),
        ),
        factory.create_primitive_list(positional_arguments),
        mappings.EMPTY,
    )


@macro("CLS_OF")
def macro_cls_of(translator: Translator, obj: tree.Expression) -> terms.Term:
    """
    Retrieves the class of the provided object.
    """
    return factory.apply(
        "record_get",
        factory.create_mem_load(translator.translate_expression(obj)),
        strings.create("cls"),
    )


@macro("VALUE_OF")
def macro_value_of(translator: Translator, obj: tree.Expression) -> terms.Term:
    """
    Retrieves the primitive value of the provided object.
    """
    return factory.apply(
        "record_get",
        factory.create_mem_load(translator.translate_expression(obj)),
        strings.create("value"),
    )


@macro("SET_VALUE")
def macro_set_value(
    translator: Translator, obj: tree.Expression, value: tree.Expression
) -> terms.Term:
    """
    Sets the primitive value of the provided object.
    """
    return factory.create_mem_store(
        translator.translate_expression(obj),
        factory.apply(
            "record_set",
            factory.create_mem_load(translator.translate_expression(obj)),
            strings.create("value"),
            translator.translate_expression(value),
        ),
    )


# endregion


# region: Memory Macros


@macro("LOAD")
def macro_load(translator: Translator, reference: tree.Expression) -> terms.Term:
    r"""
    Creates a $\tVerbSym{mem\_load}$ term for loading from a reference.
    """
    return factory.create_mem_load(translator.translate_expression(reference))


@macro("STORE")
def macro_store(
    translator: Translator, reference: tree.Expression, value: tree.Expression
) -> terms.Term:
    r"""
    Creates a $\tVerbSym{mem\_store}$ term for storing a value.
    """
    return factory.create_mem_store(
        translator.translate_expression(reference),
        translator.translate_expression(value),
    )


@macro("NEW")
def macro_new(translator: Translator, expression: tree.Expression) -> terms.Term:
    r"""
    Creates a $\tVerbSym{mem\_new}$ term for creating a new reference.
    """
    return factory.create_mem_new(translator.translate_expression(expression))


# endregion


# region: Other Macros


@macro("LITERAL")
def macro_literal(translator: Translator, expression: tree.Expression) -> terms.Term:
    """
    Casts a Python literal into a primitive literal.
    """
    if isinstance(expression, tree.String):
        return strings.create(expression.value)
    elif isinstance(expression, tree.Integer):
        return numbers.create(expression.value)
    elif isinstance(expression, tree.Float):
        return numbers.create(expression.value)
    elif isinstance(expression, tree.Tuple):
        return factory.create_primitive_list(
            [
                translator.translate_expression(element)
                for element in expression.elements
            ]
        )
    elif isinstance(expression, tree.Dict):
        if not expression.keys:
            return mappings.EMPTY
    raise NotImplementedError(
        f"macro 'LITERAL' not implemented for expression of type {type(expression)}"
    )


@macro("RECORD")
def macro_record(translator: Translator, **fields: tree.Expression) -> terms.Term:
    """
    Constructs a record with the provided fields.
    """
    return factory.apply(
        "make_record",
        factory.create_primitive_list(
            [
                factory.create_primitive_list(
                    [strings.create(name), translator.translate_expression(value),]
                )
                for name, value in fields.items()
            ]
        ),
    )


@macro("NEW_FROM_VALUE")
def macro_new_from_value(
    translator: Translator, cls: tree.Expression, value: tree.Expression
) -> terms.Term:
    r"""
    Constructs an expression utilizing $\tVerbSym{mem\_new}$ to create a
    new object of the given class with the given value.
    """
    cls_value = translator.translate_expression(cls)
    cls_field: terms.Term
    if isinstance(cls_value, references.Reference):
        cls_field = tuples.create(strings.create("cls"), cls_value)
    else:
        cls_field = factory.create_primitive_list([strings.create("cls"), cls_value])
    return factory.create_mem_new(
        factory.apply(
            "make_record",
            factory.create_primitive_list(
                [
                    cls_field,
                    tuples.create(strings.create("dict"), heap.NONE),
                    factory.create_primitive_list(
                        [
                            strings.create("value"),
                            translator.translate_expression(value),
                        ]
                    ),
                ]
            ),
        )
    )


@macro("CALL")
def macro_call(translator: Translator, frame: tree.Expression) -> terms.Term:
    r"""
    Creates a $\tVerbSym{call}$ term from the given frame.

    This macro is used by the runtime function \verb!call! for creating
    a $\tVerbSym{call}$ term which delegates control to the constructed
    frame.
    """
    return factory.create_call(translator.translate_expression(frame))


@macro("PRINT")
def macro_print(translator: Translator, expression: tree.Expression) -> terms.Term:
    r"""
    Creates a $\tVerbSym{print}$ term.
    """
    return factory.create_print(translator.translate_expression(expression))


@macro("HALT")
def macro_halt(translator: Translator) -> terms.Term:
    r"""
    Creates a $\tVerbSym{HALT}$ term useful for debugging.
    """
    return terms.symbol("HALT")


# endregion
