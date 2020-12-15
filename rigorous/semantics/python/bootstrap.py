# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import typing as t

from ...data import mappings, references, strings

from . import basis, heap, runtime

from .syntax import blocks, tree
from .translator import Translator


def _make_class(
    translator: Translator, definition: blocks.ClassDefinition
) -> heap.TypeProxy:
    identifier = definition.identifier
    reference = basis.lookup(identifier)
    if not translator.heap_builder.is_defined(reference):
        bases: t.List[references.Reference] = []
        for base in definition.bases:
            assert isinstance(base, tree.Name)
            bases.append(basis.lookup(base.identifier))
        bases.append(heap.TYPE_OBJECT)
        translator.heap_builder.new_type(
            identifier, bases=bases, layout=heap.TYPE_OBJECT, ref=reference
        )
    typ_proxy = translator.heap_builder.get_type_proxy(reference)
    _populate_class(translator, typ_proxy, definition)
    return typ_proxy


def _populate_class(
    translator: Translator,
    typ_proxy: heap.TypeProxy,
    definition: blocks.ClassDefinition,
) -> None:
    attrs = typ_proxy.attrs
    for node in definition.body:
        if isinstance(node, blocks.FunctionDefinition):
            identifier = node.identifier
            if identifier.startswith("__") and identifier.endswith("__"):
                typ_proxy.set_slot(
                    identifier, translator.translate_builtin_function(node)
                )
            else:
                attrs.setitem(
                    strings.create(identifier),
                    translator.translate_builtin_function(node),
                )
        elif isinstance(node, tree.Pass):
            pass
        else:
            assert isinstance(node, tree.Assign), f"invalid node {node} in class body"
            target = node.target
            value = node.value
            assert isinstance(
                target, tree.Name
            ), f"invalid assignment {node} in class body"
            assert (
                isinstance(value, tree.Call) and not value.arguments
            ), f"invalid assignment {node} in class body"
            function = value.function
            assert isinstance(function, tree.Name)
            typ_proxy.attrs.setitem(
                strings.create(target.identifier),
                typ_proxy.builder.new_object(cls=basis.lookup(function.identifier)),
            )


def _bootstrap() -> heap.Builder:
    translator = Translator()

    translator.heap_builder.store(
        basis.runtime_constants["BUILTINS"],
        mappings.create(
            {
                strings.create(name): constant
                for name, constant in basis.builtin_constants.items()
            }
        ),
    )

    for child in basis.runtime_module.children:
        if isinstance(child, blocks.FunctionDefinition):
            docstring: t.Optional[str] = None
            if child.body and isinstance(child.body[0], tree.Evaluate):
                if isinstance(child.body[0].expression, tree.String):
                    docstring = child.body[0].expression.value
            lineno = basis.runtime_module.locations[child].row
            runtime.define_runtime_function(
                child.identifier,
                tuple(parameter.identifier for parameter in child.parameters),
                translator.translate_runtime_function(child),
                docstring=docstring,
                lineno=lineno,
            )
        elif isinstance(child, blocks.ClassDefinition):
            _make_class(translator, child)

    for child in basis.builtins_module.children:
        if isinstance(child, blocks.ClassDefinition):
            _make_class(translator, child)
        elif isinstance(child, blocks.FunctionDefinition):
            translator.translate_builtin_function(
                child, ref=basis.builtin_constants[child.identifier]
            )

    return translator.heap_builder


_heap_builder = _bootstrap()


def create_heap_builder() -> heap.Builder:
    return _heap_builder.clone()


def create_translator() -> Translator:
    return Translator(_heap_builder.clone())
