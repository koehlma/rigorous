# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

"""
Translates a Python AST into a term.
"""

from __future__ import annotations

import dataclasses as d
import typing as t

import collections
import enum
import functools

from ...core import terms
from ...data import mappings, records, references, strings, tuples

from .syntax import blocks, tree

from . import basis, factory, heap, sugar


_SYMBOLS = {
    tree.Symbol.Kind.TRUE: heap.TRUE,
    tree.Symbol.Kind.FALSE: heap.FALSE,
    tree.Symbol.Kind.NONE: heap.NONE,
    tree.Symbol.Kind.ELLIPSIS: heap.ELLIPSIS,
}


class Mode(enum.Enum):
    USER = "user"
    PRIMITIVE = "primitive"


# FIXME: translate with assertions enabled/disabled!


@d.dataclass(frozen=False, eq=False)
class ModeManager:
    translator: Translator
    mode: Mode

    _saved_mode: t.Optional[Mode] = None

    def __enter__(self) -> None:
        self._saved_mode = self.translator.mode
        self.translator.mode = self.mode

    def __exit__(self, exc_type: t.Any, exc_value: t.Any, exc_tb: t.Any) -> None:
        assert self._saved_mode is not None
        self.translator.mode = self._saved_mode


class Translator:
    mode: Mode

    block_stack: blocks.Stack
    heap_builder: heap.Builder

    _unique_identifiers_counters: t.Dict[str, int]

    def __init__(self, heap_builder: t.Optional[heap.Builder] = None) -> None:
        self.mode = Mode.USER
        self.block_stack = blocks.Stack()
        self.heap_builder = heap_builder or heap.Builder()
        self._unique_identifiers_counters = collections.defaultdict(int)

    def enter_mode(self, mode: Mode) -> ModeManager:
        return ModeManager(self, mode)

    def _unique_identifier(self, kind: str) -> str:
        index = self._unique_identifiers_counters[kind]
        self._unique_identifiers_counters[kind] += 1
        return f"__{kind}{index}__"

    def _get_mechanism(self, identifier: str) -> blocks.Mechanism:
        if self.block_stack.is_empty:
            return blocks.Mechanism.GLOBAL
        else:
            return self.block_stack.head.get_mechanism(identifier)

    def _load(
        self, identifier: str, default: t.Optional[terms.Term] = None
    ) -> terms.Term:
        mechanism = self._get_mechanism(identifier)
        if mechanism is blocks.Mechanism.LOCAL:
            return factory.create_load_local(identifier, default=default)
        elif mechanism is blocks.Mechanism.GLOBAL:
            if self.mode is Mode.PRIMITIVE:
                if identifier in basis.builtin_constants:
                    return basis.builtin_constants[identifier]
                elif identifier in basis.runtime_constants:
                    return basis.runtime_constants[identifier]
            else:
                return sugar.create_load_global(
                    self.heap_builder.new_string(identifier)
                )
        assert self.mode is not Mode.PRIMITIVE, (
            f"invalid access mechanism {mechanism} for identifier "
            f"{identifier!r} in {self.block_stack.head}"
        )
        if mechanism is blocks.Mechanism.CELL:
            return sugar.create_load_cell(strings.create(identifier))
        elif mechanism is blocks.Mechanism.CLASS_GLOBAL:
            return sugar.create_load_class_global(
                self.heap_builder.new_string(identifier)
            )
        else:
            assert mechanism is blocks.Mechanism.CLASS_CELL
            return sugar.create_load_class_cell(
                self.heap_builder.new_string(identifier)
            )

    def _store(self, identifier: str, value: terms.Term) -> terms.Term:
        mechanism = self.block_stack.head.get_mechanism(identifier)
        if mechanism is blocks.Mechanism.LOCAL:
            return factory.create_eval(factory.create_store_local(identifier, value))
        elif mechanism is blocks.Mechanism.GLOBAL:
            return factory.create_eval(
                sugar.create_store_global(
                    self.heap_builder.new_string(identifier), value
                )
            )
        elif mechanism is blocks.Mechanism.CELL:
            return factory.create_eval(
                sugar.create_store_cell(strings.create(identifier), value)
            )
        else:
            assert mechanism in {
                blocks.Mechanism.CLASS_GLOBAL,
                blocks.Mechanism.CLASS_CELL,
            }
            return factory.create_eval(
                sugar.create_store_class(
                    self.heap_builder.new_string(identifier), value
                )
            )

    def _delete(self, identifier: str) -> terms.Term:
        mechanism = self.block_stack.head.get_mechanism(identifier)
        if mechanism is blocks.Mechanism.LOCAL:
            return factory.create_eval(factory.create_delete_local(identifier))
        elif mechanism is blocks.Mechanism.GLOBAL:
            return sugar.create_delete_global(self.heap_builder.new_string(identifier))
        elif mechanism is blocks.Mechanism.CELL:
            return sugar.create_delete_cell(strings.create(identifier))
        else:
            assert mechanism in {
                blocks.Mechanism.CLASS_GLOBAL,
                blocks.Mechanism.CLASS_CELL,
            }
            return sugar.create_delete_class(self.heap_builder.new_string(identifier))

    @functools.singledispatchmethod
    def _translate(self, node: tree.AST) -> terms.Term:
        raise NotImplementedError(f"`_translate` not implemented for {type(node)}")

    @_translate.register
    def _translate_name(self, ast: tree.Name) -> terms.Term:
        # other contexts are handeld by `_translate_assign` and `_translate_delete`
        assert ast.context is tree.Context.LOAD
        return self._load(ast.identifier)

    @_translate.register
    def _translate_string(self, ast: tree.String) -> terms.Term:
        return self.heap_builder.new_string(ast.value)

    @_translate.register
    def _translate_integer(self, ast: tree.Integer) -> terms.Term:
        return self.heap_builder.new_int(ast.value)

    @_translate.register
    def _translate_float(self, ast: tree.Float) -> terms.Term:
        return self.heap_builder.new_float(ast.value)

    @_translate.register
    def _translate_symbol(self, ast: tree.Symbol) -> terms.Term:
        return _SYMBOLS[ast.kind]

    @_translate.register
    def _translate_list(self, ast: tree.List) -> terms.Term:
        return sugar.create_make_list(
            factory.create_primitive_list(
                [self._translate(element) for element in ast.elements]
            )
        )

    @_translate.register
    def _translate_tuple(self, ast: tree.Tuple) -> terms.Term:
        return sugar.create_make_tuple(
            factory.create_primitive_list(
                [self._translate(element) for element in ast.elements]
            )
        )

    @_translate.register
    def _translate_dict(self, ast: tree.Dict) -> terms.Term:
        return sugar.create_make_dict(
            factory.create_primitive_list(
                [
                    factory.create_primitive_list(
                        [self._translate(key), self._translate(value)]
                    )
                    for key, value in ast.items
                ]
            )
        )

    @_translate.register
    def _translate_unary(self, ast: tree.Unary) -> terms.Term:
        return sugar.create_eval_unary(ast.operator, self._translate(ast.operand))

    @_translate.register
    def _translate_not(self, ast: tree.Not) -> terms.Term:
        return sugar.create_eval_not(self._translate(ast.operand))

    @_translate.register
    def _translate_binary(self, ast: tree.Binary) -> terms.Term:
        return sugar.create_eval_binary(
            ast.operator, self._translate(ast.left), self._translate(ast.right)
        )

    @_translate.register
    def _translate_boolean(self, ast: tree.Boolean) -> terms.Term:
        return factory.create_binary(
            self._translate(ast.left), ast.operator, self._translate(ast.right)
        )

    @_translate.register
    def _translate_conditional(self, ast: tree.Conditional) -> terms.Term:
        return factory.create_ternary(
            factory.create_bool(self._translate(ast.condition)),
            self._translate(ast.consequent),
            self._translate(ast.alternate),
        )

    @_translate.register
    def _translate_comparison(self, ast: tree.Comparison) -> terms.Term:
        result = self._translate(ast.comparators[-1].value)
        for left, right in reversed(tuple(zip(ast.comparators, ast.comparators[1:]))):
            result = factory.create_binary(
                self._translate(left.value), right.operator, result
            )
        return factory.create_compare(
            factory.create_binary(
                self._translate(ast.left), ast.comparators[0].operator, result
            )
        )

    def _translate_arguments(
        self, arguments: t.Sequence[tree.Argument]
    ) -> t.Tuple[terms.Term, terms.Term]:
        positional_arguments: terms.Term = factory.create_primitive_nil()
        keyword_arguments: terms.Term = mappings.EMPTY
        for argument in reversed(arguments):
            if argument.kind is tree.ArgumentKind.POSITIONAL:
                positional_arguments = factory.create_primitive_cons(
                    self._translate(argument.value), positional_arguments
                )
            elif argument.kind is tree.ArgumentKind.UNPACK_POSITIONAL:
                positional_arguments = sugar.create_unpack_positional(
                    self._translate(argument.value), positional_arguments,
                )
            elif argument.kind is tree.ArgumentKind.KEYWORD:
                assert argument.name is not None
                keyword_arguments = sugar.create_keyword_add(
                    strings.create(argument.name),
                    self._translate(argument.value),
                    keyword_arguments,
                )
            else:
                assert argument.kind is tree.ArgumentKind.UNPACK_KEYWORDS
                keyword_arguments = sugar.create_unpack_keywords(
                    self._translate(argument.value), keyword_arguments
                )
        return positional_arguments, keyword_arguments

    @_translate.register
    def _translate_call(self, ast: tree.Call) -> terms.Term:
        if isinstance(ast.function, tree.Name):
            identifier = ast.function.identifier
            mechanism = self.block_stack.head.get_mechanism(identifier)
            if self.mode is Mode.PRIMITIVE and mechanism is not blocks.Mechanism.LOCAL:
                if basis.macros.is_macro(identifier):
                    return basis.macros.get_macro(identifier)(
                        self,
                        *(
                            argument.value
                            for argument in ast.arguments
                            if argument.kind is tree.ArgumentKind.POSITIONAL
                        ),
                        **{
                            argument.name: argument.value
                            for argument in ast.arguments
                            if argument.name is not None
                        },
                    )
                elif basis.primitives.is_primitive(identifier):
                    assert all(
                        argument.kind is tree.ArgumentKind.POSITIONAL
                        for argument in ast.arguments
                    )
                    return factory.apply(
                        identifier,
                        *(
                            self.translate_expression(argument.value)
                            for argument in ast.arguments
                        ),
                    )
                elif ast.function.identifier in basis.runtime_functions:
                    assert all(
                        argument.kind is tree.ArgumentKind.POSITIONAL
                        for argument in ast.arguments
                    )
                    return factory.runtime(
                        ast.function.identifier,
                        *(
                            self.translate_expression(argument.value)
                            for argument in ast.arguments
                        ),
                    )
            if (
                ast.function.identifier == "super"
                and isinstance(self.block_stack.predecessor, blocks.ClassDefinition)
                and not ast.arguments
            ):
                definition = self.block_stack.head
                if (
                    isinstance(definition, blocks.FunctionDefinition)
                    and definition.parameters
                ):
                    # Translate this call to `super` according to PEP 3135:
                    # https://www.python.org/dev/peps/pep-3135/#specification
                    #
                    # Note: What we are doing here is valid as far as I understand
                    # the specification. However, this is not what CPython does.
                    # CPython takes the `__class__` cell and first argument from the
                    # predecessor frame of super on the stack:
                    # https://github.com/python/cpython/blob/a6109ef68d421712ba368ef502c4789e8de113e0/Objects/typeobject.c#L8158

                    return factory.runtime(
                        "class_super",
                        factory.runtime(
                            "load__class__", factory.create_load_local("__cells__"),
                        ),
                        self._load(
                            definition.parameters[0].identifier, default=heap.NONE,
                        ),
                    )
        positional_arguments, keyword_arguments = self._translate_arguments(
            ast.arguments
        )
        return sugar.create_call(
            self._translate(ast.function), positional_arguments, keyword_arguments,
        )

    @_translate.register
    def _translate_yield(self, ast: tree.Yield) -> terms.Term:
        return factory.create_yield(self._translate(ast.value))

    @_translate.register
    def _translate_attribute(self, ast: tree.Attribute) -> terms.Term:
        return sugar.create_eval_getattr(
            self._translate(ast.value), self.heap_builder.new_string(ast.name)
        )

    @_translate.register
    def _translate_item(self, ast: tree.Item) -> terms.Term:
        return sugar.create_eval_getitem(
            self._translate(ast.value), self._translate(ast.key)
        )

    @_translate.register
    def _translate_lambda(self, ast: tree.Lambda) -> terms.Term:
        return self._translate_function(ast.definition)

    @_translate.register
    def _translate_evaluate(self, ast: tree.Evaluate) -> terms.Term:
        return factory.create_eval(self._translate(ast.expression))

    @_translate.register
    def _translate_assign(self, ast: tree.Assign) -> terms.Term:
        value = self._translate(ast.value)
        if isinstance(ast.target, tree.Name):
            assert ast.target.context is tree.Context.STORE
            return self._store(ast.target.identifier, value)
        elif isinstance(ast.target, tree.Attribute):
            return sugar.create_set_attribute(
                self._translate(ast.target.value),
                self.heap_builder.new_string(ast.target.name),
                value,
            )
        else:
            assert isinstance(ast.target, tree.Item)
            return sugar.create_setitem(
                self._translate(ast.target.value),
                self._translate(ast.target.key),
                value,
            )

    @_translate.register
    def _translate_delete(self, ast: tree.Delete) -> terms.Term:
        if isinstance(ast.target, tree.Name):
            return self._delete(ast.target.identifier)
        elif isinstance(ast.target, tree.Attribute):
            print("delete attribute", ast.target.name)
            return sugar.create_delete_attribute(
                self._translate(ast.target.value),
                self.heap_builder.new_string(ast.target.name),
            )
        else:
            assert isinstance(ast.target, tree.Item)
            return sugar.create_delete_item(
                self._translate(ast.target.value),
                self.translate_expression(ast.target.key),
            )

    @_translate.register
    def _translate_raise(self, ast: tree.Raise) -> terms.Term:
        if ast.exception is None:
            return sugar.create_raise()
        else:
            return sugar.create_raise(self._translate(ast.exception))

    @_translate.register
    def _translate_assert(self, ast: tree.Assert) -> terms.Term:
        return sugar.create_if(
            self._translate(tree.Not(ast.condition)),
            factory.create_raise(
                factory.runtime(
                    "create_assertion_error",
                    self._translate(ast.message) if ast.message else heap.NONE,
                )
            ),
        )

    @_translate.register
    def _translate_pass(self, ast: tree.Pass) -> terms.Term:
        return factory.create_pass()

    @_translate.register
    def _translate_if(self, ast: tree.If) -> terms.Term:
        return sugar.create_if(
            self.translate_expression(ast.condition),
            consequent=self.translate_body(ast.consequence),
            alternate=self.translate_body(ast.alternate),
        )

    @_translate.register
    def _translate_for(self, ast: tree.For) -> terms.Term:
        iterator_id = self._unique_identifier("iterator")
        check_next_id = self._unique_identifier("check_next")
        return factory.create_sequence(
            factory.create_sequence(
                factory.create_eval(
                    factory.create_store_local(
                        iterator_id,
                        factory.runtime(
                            "runtime_iter", self.translate_expression(ast.iterator),
                        ),
                    )
                ),
                factory.create_eval(
                    factory.create_store_local(check_next_id, heap.TRUE)
                ),
            ),
            sugar.create_while(
                factory.create_load_local(check_next_id),
                factory.create_try_except(
                    self._store(
                        ast.target.identifier,
                        sugar.create_call(
                            basis.builtin_constants["next"],
                            factory.create_primitive_list(
                                [factory.create_load_local(iterator_id)]
                            ),
                            mappings.EMPTY,
                        ),
                    ),
                    sugar.create_if(
                        factory.runtime(
                            "is_exception_compatible",
                            factory.create_get_active_exc(),
                            basis.builtin_constants["StopIteration"],
                        ),
                        factory.create_eval(
                            factory.create_store_local(check_next_id, heap.FALSE)
                        ),
                        sugar.create_raise(),
                    ),
                    self.translate_body(ast.body),
                ),
                self.translate_body(ast.alternate),
            ),
        )

    @_translate.register
    def _translate_while(self, ast: tree.While) -> terms.Term:
        return sugar.create_while(
            self._translate(ast.condition),
            self.translate_body(ast.body),
            self.translate_body(ast.alternate),
        )

    @_translate.register
    def _translate_loop_control(self, ast: tree.LoopControl) -> terms.Term:
        if ast.kind is tree.LoopControl.Kind.BREAK:
            return factory.create_break()
        else:
            assert ast.kind is tree.LoopControl.Kind.CONTINUE
            return factory.create_continue()

    @_translate.register
    def _translate_try(self, ast: tree.Try) -> terms.Term:
        body = self.translate_body(ast.body)
        if ast.alternate:
            alternative = self.translate_body(ast.alternate)
        else:
            alternative = factory.create_pass()

        previous_handler = sugar.create_raise()
        for handler in reversed(ast.handlers):
            handler_body = self.translate_body(handler.body)
            if handler.target:
                handler_body = factory.create_sequence(
                    self._store(
                        handler.target.identifier, factory.create_get_active_exc(),
                    ),
                    sugar.create_try_finally(
                        handler_body,
                        factory.create_try_except(
                            self._delete(handler.target.identifier),
                            sugar.create_if(
                                factory.create_bool(
                                    factory.runtime(
                                        "is_exception_compatible",
                                        factory.create_get_active_exc(),
                                        basis.lookup("NameError"),
                                    )
                                ),
                                factory.create_pass(),
                                sugar.create_raise(),
                            ),
                            factory.create_pass(),
                        ),
                    ),
                )
            if handler.pattern:
                previous_handler = factory.create_if(
                    factory.create_bool(
                        factory.runtime(
                            "is_exception_compatible",
                            factory.create_get_active_exc(),
                            self.translate_expression(handler.pattern),
                        )
                    ),
                    handler_body,
                    previous_handler,
                )
            else:
                previous_handler = handler_body

        assert previous_handler is not None
        body = factory.create_try_except(body, previous_handler, alternative)
        if ast.final:
            return factory.create_try_finally(body, self.translate_body(ast.final))
        return body

    @_translate.register
    def _translate_return(self, ast: tree.Return) -> terms.Term:
        return factory.create_return(self._translate(ast.value))

    @_translate.register
    def _translate_scope_modifier(self, ast: tree.ScopeModifier) -> terms.Term:
        return factory.create_pass()

    def _translate_function(self, ast: blocks.FunctionDefinition) -> terms.Term:
        code = self.translate_code(ast)
        defaults: terms.Term = mappings.EMPTY
        for parameter in reversed(ast.parameters):
            if parameter.default:
                defaults = factory.apply(
                    "mapping_set",
                    defaults,
                    strings.create(parameter.identifier),
                    self.translate_expression(parameter.default),
                )
        func = factory.runtime(
            "build_function",
            code,
            factory.create_load_local("__globals__"),
            factory.create_load_local("__cells__"),
            defaults,
        )
        for decorator in reversed(ast.decorators):
            func = sugar.create_call(
                self.translate_expression(decorator),
                factory.create_primitive_list([func]),
                mappings.EMPTY,
            )
        return func

    @_translate.register
    def _translate_function_definition(
        self, ast: blocks.FunctionDefinition
    ) -> terms.Term:
        return self._store(ast.identifier, self._translate_function(ast))

    @_translate.register
    def _translate_class_definition(self, ast: blocks.ClassDefinition) -> terms.Term:
        with self.block_stack.enter(ast):
            body = factory.create_sequence(
                self._store("__module__", self.heap_builder.new_string("__main__")),
                factory.create_sequence(
                    self._store("__doc__", self.get_docstring(ast.body)),
                    factory.create_sequence(
                        self.translate_body(ast.body), factory.create_return(heap.NONE),
                    ),
                ),
            )
        code = self.heap_builder.new_code(
            body,
            name=ast.identifier,
            signature=tuples.create(
                records.create(
                    name=strings.create("__dict__"),
                    kind=strings.create(
                        blocks.ParameterKind.POSITIONAL_OR_KEYWORD.name
                    ),
                ),
            ),
        )
        func = factory.runtime(
            "build_function",
            code,
            factory.create_load_local("__globals__"),
            factory.create_load_local("__cells__"),
            mappings.EMPTY,
        )
        positional_arguments, keyword_arguments = self._translate_arguments(
            ast.arguments
        )
        positional_arguments = factory.create_primitive_cons(
            self.heap_builder.new_string(ast.identifier), positional_arguments
        )
        positional_arguments = factory.create_primitive_cons(func, positional_arguments)
        cls = sugar.create_call(
            basis.lookup("__build_class__"), positional_arguments, keyword_arguments,
        )
        for decorator in reversed(ast.decorators):
            cls = sugar.create_call(
                self.translate_expression(decorator),
                factory.create_primitive_list([cls]),
                mappings.EMPTY,
            )
        return self._store(ast.identifier, cls)

    def translate_code(
        self, definition: blocks.FunctionDefinition
    ) -> references.Reference:
        with self.block_stack.enter(definition):
            signature: t.List[records.Record] = []
            for parameter in definition.parameters:
                signature.append(
                    records.create(
                        name=strings.create(parameter.identifier),
                        kind=strings.create(parameter.kind.name),
                    )
                )
            body = factory.create_sequence(
                self.translate_body(definition.body), factory.create_return(heap.NONE),
            )
            if definition.contains_yield:
                body = factory.create_sequence(
                    factory.create_eval(factory.create_return_point()), body
                )
            return self.heap_builder.new_code(
                name=definition.identifier,
                body=body,
                signature=tuples.create(*signature),
                is_generator=definition.contains_yield,
                doc=self.get_docstring(definition.body),
                cells=tuple(
                    identifier
                    for identifier in definition.bound_names
                    if definition.get_mechanism(identifier) is blocks.Mechanism.CELL
                ),
            )

    def translate_expression(self, expression: tree.Expression) -> terms.Term:
        return self._translate(expression)

    def translate_body(self, body: t.Sequence[tree.Statement]) -> terms.Term:
        if not body:
            return factory.create_pass()
        right = self._translate(body[-1])
        for left in reversed(body[:-1]):
            statement = self._translate(left)
            # optimize away unnecessary `pass` statements
            if statement != terms.symbol("pass"):
                right = factory.create_sequence(statement, right)
        return right

    def translate_builtin_function(
        self, definition: blocks.FunctionDefinition, *, ref: heap.Ref = None
    ) -> references.Reference:
        with self.enter_mode(Mode.PRIMITIVE):

            code = self.translate_code(definition)
            defaults: t.Dict[strings.String, terms.Term] = {}
            for parameter in definition.parameters:
                if parameter.default is not None:
                    value = self.translate_expression(parameter.default)
                    assert isinstance(value, references.Reference)
                    defaults[strings.create(parameter.identifier)] = value
            return self.heap_builder.new_function(
                name=definition.identifier,
                code=code,
                global_namespace=heap.BUILTIN_GLOBALS,
                defaults=mappings.create(
                    t.cast(t.Mapping[terms.Term, terms.Term], defaults)
                ),
                ref=ref,
            )

    def translate_runtime_function(
        self, definition: blocks.FunctionDefinition
    ) -> terms.Term:
        with self.enter_mode(Mode.PRIMITIVE), self.block_stack.enter(definition):
            return factory.create_sequence(
                self.translate_body(definition.body), factory.create_return(heap.NONE),
            )

    def get_docstring(self, body: t.Sequence[tree.Statement]) -> terms.Term:
        if body and isinstance(body[0], tree.Evaluate):
            if isinstance(body[0].expression, tree.String):
                return self.heap_builder.new_string(body[0].expression.value)
        return heap.NONE

    def translate_module(self, module: blocks.Module) -> terms.Term:
        with self.block_stack.enter(module):
            return factory.create_sequence(
                self._store("__name__", self.heap_builder.new_string("__main__")),
                factory.create_sequence(
                    self._store("__doc__", self.get_docstring(module.body)),
                    factory.create_sequence(
                        self.translate_body(module.body),
                        factory.create_return(heap.NONE),
                    ),
                ),
            )
