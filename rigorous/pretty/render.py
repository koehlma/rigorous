# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import dataclasses as d
import typing as t

import abc
import functools

from mxu.itertools import iter_lookahead

from ..core import inference, terms, unification
from ..data import (
    booleans,
    mappings,
    null,
    numbers,
    records,
    sets,
    strings,
    tuples,
    references,
)

from . import define


class Element(abc.ABC):
    pass


@d.dataclass(frozen=True)
class Chunk(Element):
    text: str
    math: t.Optional[str] = None


@d.dataclass(frozen=True)
class Box(Element):
    elements: t.Tuple[Element, ...]
    truncate: bool = False
    term: t.Optional[terms.Term] = None
    special: t.Optional[Special] = None


class Special(Element, abc.ABC):
    pass


class RenderSpecial(t.Protocol):
    def __call__(self, *args: Box) -> Special:
        pass


@d.dataclass(frozen=True)
class SpecialPattern:
    pattern: terms.Term
    variables: t.Tuple[terms.Variable, ...]
    render: RenderSpecial


@d.dataclass(eq=False)
class BoxBuilder:
    renderer: Renderer
    elements: t.List[Element] = d.field(default_factory=list)
    truncate: bool = False
    special: t.Optional[Special] = None

    def build(
        self,
        term: t.Optional[terms.Term] = None,
        *,
        special: t.Optional[Special] = None,
    ) -> Box:
        return Box(
            tuple(self.elements),
            truncate=self.truncate,
            term=term,
            special=special or self.special,
        )

    def append_chunk(self, text: str, *, math: t.Optional[str] = None) -> None:
        self.elements.append(Chunk(text, math=math))

    def append_term(self, term: terms.Term) -> None:
        self.elements.append(self.renderer.render_term(term))


@d.dataclass(eq=False)
class Renderer:
    _special_patterns: t.List[SpecialPattern] = d.field(default_factory=list)
    _symbol_to_math: t.Dict[str, str] = d.field(default_factory=dict)

    def add_pattern(self, pattern: SpecialPattern) -> None:
        self._special_patterns.append(pattern)

    def add_math_symbol(self, symbol: str, math: str) -> None:
        self._symbol_to_math[symbol] = math

    def render_condition(
        self,
        condition: inference.Condition,
        substitution: t.Optional[terms.Substitution] = None,
    ) -> Box:
        builder = BoxBuilder(self)
        render_condition(condition, builder, substitution)
        return builder.build()

    def render_term(self, term: terms.Term) -> Box:
        builder = BoxBuilder(self)
        self._render_term(term, builder)
        special = None
        for pattern in self._special_patterns:
            substitution = unification.match(pattern.pattern, term)
            if substitution is not None:
                special = pattern.render(
                    *(
                        self.render_term(substitution[variable])
                        for variable in pattern.variables
                    ),
                )
                break
        return builder.build(term=term, special=special)

    @functools.singledispatchmethod
    def _render_term(self, term: terms.Term, builder: BoxBuilder) -> None:
        raise NotImplementedError(f"`_render_term` not implemented for {type(term)}")

    @_render_term.register
    def _render_variable(self, term: terms.Variable, builder: BoxBuilder) -> None:
        info = define.get_variable_info(term)
        text = term.name
        math = term.name
        if info is not None:
            text = info.text or term.name
            math = info.math
        builder.append_chunk(text or "unnamed", math=math)

    @_render_term.register
    def _render_symbol(self, term: terms.Symbol, builder: BoxBuilder) -> None:
        builder.append_chunk(
            term.symbol, math=self._symbol_to_math.get(term.symbol, None)
        )

    @_render_term.register
    def _render_sequence(self, term: terms.Sequence, builder: BoxBuilder) -> None:
        builder.append_chunk("(", math="\\left(")
        for child, lookahead in iter_lookahead(term.elements):
            builder.append_term(child)
            if lookahead:
                builder.append_chunk(" ", math="\\ ")
        builder.append_chunk(")", math="\\right)")

    @_render_term.register
    def _render_value(self, term: terms.Value, builder: BoxBuilder) -> None:
        render_value(term, builder)

    @_render_term.register
    def _render_apply(self, term: terms.Apply, builder: BoxBuilder) -> None:
        render_operator(term.operator, term.arguments, builder)


@functools.singledispatch
def render_value(value: terms.Value, builder: BoxBuilder) -> None:
    raise NotImplementedError(f"`render_value` not implemented for {value}")


@functools.singledispatch
def render_operator(
    operator: terms.Operator, arguments: terms.Arguments, builder: BoxBuilder
) -> None:
    raise NotImplementedError(f"`render_operator` not implemented for {operator}")


@functools.singledispatch
def render_condition(
    condition: inference.Condition,
    builder: BoxBuilder,
    substitution: t.Optional[terms.Substitution] = None,
) -> None:
    raise NotImplementedError(f"`render_condition` not implemented for {condition}")


@render_condition.register
def render_boolean_condition(
    condition: booleans.BooleanCondition,
    builder: BoxBuilder,
    substitution: t.Optional[terms.Substitution] = None,
) -> None:
    builder.append_term(condition.term.substitute(substitution or {}))


class RenderFunctionOperator(t.Protocol):
    def __call__(self, arguments: terms.Arguments, builder: BoxBuilder) -> None:
        pass


_render_function_operator: t.Dict[terms.FunctionOperator, RenderFunctionOperator] = {}


def register_function_operator(
    operator: terms.FunctionOperator,
) -> t.Callable[[RenderFunctionOperator], RenderFunctionOperator]:
    def decorator(render: RenderFunctionOperator) -> RenderFunctionOperator:
        _render_function_operator[operator] = render
        return render

    return decorator


@render_operator.register
def render_function_operator(
    operator: terms.FunctionOperator, arguments: terms.Arguments, builder: BoxBuilder,
) -> None:
    try:
        render = _render_function_operator[operator]
    except KeyError:
        if operator.name is not None:
            builder.append_chunk(
                operator.name, math=f"\\applyFunction{{\\texttt{{{operator.name}}}}}",
            )
            builder.append_chunk("(", math="{{")
            for argument, lookahead in iter_lookahead(arguments):
                builder.append_term(argument)
                if lookahead:
                    builder.append_chunk(", ", math=",\\ ")
            builder.append_chunk(")", math="}}")
        else:
            error_operator = operator.name or operator.implementation
            raise NotImplementedError(
                f"rendering function for {error_operator!r} not implemented"
            )
    else:
        render(arguments, builder)


@register_function_operator(terms.replace)
def render_replace(arguments: terms.Arguments, builder: BoxBuilder) -> None:
    builder.append_term(arguments[0])
    builder.append_chunk("[", math="\\mxPreApplySkip\\left[")
    builder.append_term(arguments[1])
    builder.append_chunk(" ↦ ", math="\\mapsto")
    builder.append_term(arguments[2])
    builder.append_chunk("]", math="\\right]")


@register_function_operator(booleans.lnot)
def render_booleans_lnot(arguments: terms.Arguments, builder: BoxBuilder) -> None:
    builder.append_chunk("¬", math="\\lnot")
    builder.append_term(arguments[0])


@register_function_operator(mappings.getitem)
def render_getitem(arguments: terms.Arguments, builder: BoxBuilder) -> None:
    builder.append_term(arguments[0])
    builder.append_chunk("[", math="\\mxPreApplySkip\\left[")
    builder.append_term(arguments[1])
    builder.append_chunk("]", math="\\right]")
    if len(arguments) == 3:
        builder.append_chunk("?", math="?")
        builder.append_term(arguments[2])


@register_function_operator(mappings.setitem)
def render_setitem(arguments: terms.Arguments, builder: BoxBuilder) -> None:
    builder.append_term(arguments[0])
    builder.append_chunk("[", math="\\left[")
    builder.append_term(arguments[1])
    builder.append_chunk(" ↦ ", math="\\mapsto")
    builder.append_term(arguments[2])
    builder.append_chunk("]", math="\\right]")


@register_function_operator(records.getfield_operator)
def render_getfield(arguments: terms.Arguments, builder: BoxBuilder) -> None:
    builder.append_term(arguments[0])
    field = arguments[1]
    builder.append_chunk(".", math=".")
    if isinstance(field, strings.String):
        builder.append_chunk(field.value, math=f"\\texttt{{{field.value}}}")
    else:
        builder.append_term(field)


@register_function_operator(records.setfield_operator)
def render_setfield(arguments: terms.Arguments, builder: BoxBuilder) -> None:
    builder.append_chunk("(", math="\\left(")
    builder.append_term(arguments[0])
    field = arguments[1]
    builder.append_chunk(".", math=".")
    if isinstance(field, strings.String):
        builder.append_chunk(field.value, math=f"\\texttt{{{field.value}}}")
    else:
        builder.append_term(field)
    builder.append_chunk(" := ", math=":=")
    builder.append_term(arguments[2])
    builder.append_chunk(")", math="\\right)")


@register_function_operator(tuples.project_operator)
def render_project(arguments: terms.Arguments, builder: BoxBuilder) -> None:
    index = arguments[1]
    if isinstance(index, numbers.Integer):
        builder.append_chunk(f"#{index.value}")
        builder.append_chunk("(", math="\\left(")
        builder.append_term(arguments[0])
        builder.append_chunk(")", math="\\right)")
    else:
        builder.append_term(arguments[0])
        builder.append_chunk("[", math="\\left[")
        builder.append_term(index)
        builder.append_chunk("]", math="\\right]")


@register_function_operator(sets.not_contains)
def _render_sets_not_contains(arguments: terms.Arguments, builder: BoxBuilder) -> None:
    builder.append_term(arguments[1])
    builder.append_chunk(" ∉ ", math="\\not\\in")
    builder.append_term(arguments[0])


@register_function_operator(sets.contains)
def _render_sets_contains(arguments: terms.Arguments, builder: BoxBuilder) -> None:
    builder.append_term(arguments[1])
    builder.append_chunk(" ∈ ", math="\\in")
    builder.append_term(arguments[0])


@register_function_operator(records.construct)
def _render_records_construct(arguments: terms.Arguments, builder: BoxBuilder) -> None:
    builder.append_chunk("⟨", math="\\left\\langle")
    for (field_name, field_value), lookahead in iter_lookahead(
        zip(arguments[::2], arguments[1::2])
    ):
        builder.append_term(field_name)
        builder.append_chunk(": ", math=":")
        builder.append_term(field_value)
        if lookahead:
            builder.append_chunk(", ", math=",")
    builder.append_chunk("⟩", math="\\right\\rangle")


def register_binary_infix_operator(
    operator: terms.FunctionOperator,
    text: str,
    *,
    math: t.Optional[str] = None,
    prefix: t.Optional[Chunk] = None,
    suffix: t.Optional[Chunk] = None,
) -> None:
    @register_function_operator(operator)
    def _render_operator(arguments: terms.Arguments, builder: BoxBuilder) -> None:
        if prefix is not None:
            builder.append_chunk(prefix.text, math=prefix.math)
        builder.append_term(arguments[0])
        builder.append_chunk(text, math=math)
        builder.append_term(arguments[1])
        if suffix is not None:
            builder.append_chunk(suffix.text, math=suffix.math)


register_binary_infix_operator(numbers.add, " + ", math="+")
register_binary_infix_operator(numbers.sub, " - ", math="-")
register_binary_infix_operator(numbers.mul, " · ", math="\\cdot")
register_binary_infix_operator(numbers.real_div, " ÷ ", math="\\div")
register_binary_infix_operator(
    numbers.floor_div,
    " ÷ ",
    math="\\div",
    prefix=Chunk("⌊", math="\\left\\lfloor"),
    suffix=Chunk("⌋", math="\\right\\rfloor"),
)
register_binary_infix_operator(booleans.equals, " = ", math="=")
register_binary_infix_operator(booleans.not_equals, " ≠ ", math="\\neq")
register_binary_infix_operator(booleans.lor, " ∨ ", math="\\lor")


@render_value.register
def _render_boolean(value: booleans.Boolean, builder: BoxBuilder) -> None:
    if value.value:
        builder.append_chunk("true", math="\\texttt{true}")
    else:
        builder.append_chunk("false", math="\\texttt{false}")


@render_value.register
def _render_mapping(value: mappings.Mapping, builder: BoxBuilder) -> None:
    builder.append_chunk("{", math="\\left\\{")
    for (key, term), lookahead in iter_lookahead(value.entries.items()):
        builder.append_term(key)
        builder.append_chunk(" ↦ ", math="\\mapsto")
        builder.append_term(term)
        if lookahead:
            builder.append_chunk(", ", math=",")
    builder.append_chunk("}", math="\\right\\}")


@render_value.register
def _render_heap(value: references.Heap, builder: BoxBuilder) -> None:
    builder.append_chunk("{", math="\\left\\{")
    builder.append_chunk("HEAP")
    builder.append_chunk("}", math="\\right\\}")


@render_value.register
def _render_number(value: numbers.Number, builder: BoxBuilder) -> None:
    builder.append_chunk(str(value.value), math=str(value.value))


@render_value.register
def _render_null(value: null.Null, builder: BoxBuilder) -> None:
    builder.append_chunk("⊥", math="\\bot")


@render_value.register
def _render_string(value: strings.String, builder: BoxBuilder) -> None:
    builder.append_chunk(
        f"{value.value!r}", math=f"\\text{{`\\texttt{{{value.value}}}'}}"
    )


@render_value.register
def _render_record(value: records.Record, builder: BoxBuilder) -> None:
    builder.append_chunk("⟨", math="\\left\\langle")
    for (field_name, field_value), lookahead in iter_lookahead(value.fields.items()):
        builder.append_chunk(field_name)
        builder.append_chunk(": ", math=":")
        builder.append_term(field_value)
        if lookahead:
            builder.append_chunk(", ", math=",")
    builder.append_chunk("⟩", math="\\right\\rangle")


@render_value.register
def _render_tuple(value: tuples.Tuple, builder: BoxBuilder) -> None:
    builder.append_chunk("⟨", math="\\left[\\,")
    for component, lookahead in iter_lookahead(value.components):
        builder.append_term(component)
        if lookahead:
            builder.append_chunk(", ", math=",")
    builder.append_chunk("⟩", math="\\,\\right]")


@render_value.register
def _render_set(value: sets.Set, builder: BoxBuilder) -> None:
    builder.append_chunk("{", math="\\left\\{")
    for member, lookahead in iter_lookahead(value.members):
        builder.append_term(member)
        if lookahead:
            builder.append_chunk(", ", math=",\\ ")
    builder.append_chunk("}", math="\\right\\}")


@render_value.register
def _render_reference(value: references.Reference, builder: BoxBuilder) -> None:
    builder.append_chunk(f"ref({value.name or value.address})")


default_renderer = Renderer()
