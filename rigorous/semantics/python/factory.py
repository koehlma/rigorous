# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import typing as t

from ...core import terms
from ...data import null, strings, tuples

from .syntax import operators


def create_identifier(identifier: t.Union[terms.Term, str]) -> terms.Term:
    if isinstance(identifier, str):
        return strings.create(identifier)
    return identifier


def create_load_local(
    identifier: t.Union[terms.Term, str], default: t.Optional[terms.Term] = None
) -> terms.Term:
    return terms.sequence(
        "load_local", create_identifier(identifier), default or null.NULL
    )


def create_primitive_nil() -> terms.Term:
    return tuples.EMPTY


def create_primitive_cons(head: terms.Term, tail: terms.Term) -> terms.Term:
    return terms.sequence(head, "::", tail)


def create_primitive_list(
    elements: t.Sequence[terms.Term], tail: terms.Term = tuples.EMPTY
) -> terms.Term:
    for element in reversed(elements):
        tail = create_primitive_cons(element, tail)
    return tail


def create_keyword(name: t.Union[terms.Term, str], value: terms.Term) -> terms.Term:
    if isinstance(name, str):
        name = strings.create(name)
    return terms.sequence(name, "=", value)


def create_unary(
    operator: t.Union[terms.Variable, operators.UnaryOperator], operand: terms.Term,
) -> terms.Term:
    operator_term: terms.Term
    if isinstance(operator, operators.UnaryOperator):
        operator_term = terms.symbol(operator.symbol)
    else:
        operator_term = operator
    return terms.sequence(operator_term, operand)


def create_binary(
    left: terms.Term,
    operator: t.Union[
        terms.Term,
        operators.BinaryOperator,
        operators.ComparisonOperator,
        operators.BooleanOperator,
    ],
    right: terms.Term,
) -> terms.Term:
    if isinstance(operator, terms.Term):
        operator_term = operator
    else:
        operator_term = terms.symbol(operator.symbol)
    return terms.sequence(left, operator_term, right)


def create_compare(expr: terms.Term) -> terms.Term:
    return terms.sequence("cmp", expr)


def create_call(frame: terms.Term) -> terms.Term:
    return terms.sequence("call", frame)


def create_yield(value: terms.Term) -> terms.Term:
    return terms.sequence("yield", value)


def create_mem_load(reference: terms.Term) -> terms.Term:
    return terms.sequence("mem_load", reference)


def create_mem_store(reference: terms.Term, value: terms.Term) -> terms.Term:
    return terms.sequence("mem_store", reference, value)


def create_store_local(
    identifier: t.Union[terms.Term, str], value: terms.Term
) -> terms.Term:
    return terms.sequence("store_local", create_identifier(identifier), value)


def create_eval(expression: terms.Term) -> terms.Term:
    return terms.sequence("eval", expression)


def create_delete_local(identifier: t.Union[terms.Term, str]) -> terms.Term:
    return terms.sequence("delete_local", create_identifier(identifier))


def create_del_global(identifier: t.Union[terms.Term, str]) -> terms.Term:
    return terms.sequence("del_global", create_identifier(identifier))


def create_del_cell(identifier: t.Union[terms.Term, str]) -> terms.Term:
    return terms.sequence("del_cell", create_identifier(identifier))


def create_del_class(identifier: t.Union[terms.Term, str]) -> terms.Term:
    return terms.sequence("del_class", create_identifier(identifier))


def create_del_attribute(
    target: terms.Term, field: t.Union[terms.Term, str]
) -> terms.Term:
    if isinstance(field, str):
        field = strings.create(field)
    return terms.sequence("del", target, ".", field)


def create_del_item(target: terms.Term, key: terms.Term) -> terms.Term:
    return terms.sequence("del", target, "[", key, "]")


def create_raise(exception: t.Optional[terms.Term] = None) -> terms.Term:
    if exception is None:
        return terms.symbol("raise")
    else:
        return terms.sequence("raise", exception)


def create_assert(condition: terms.Term, message: terms.Term) -> terms.Term:
    return terms.sequence("assert", condition, message)


def create_pass() -> terms.Term:
    return terms.symbol("pass")


def create_if(
    condition: terms.Term, consequence: terms.Term, alternative: terms.Term
) -> terms.Term:
    return terms.sequence("if", condition, "then", consequence, "else", alternative)


def create_while_loop(
    condition: terms.Term, body: terms.Term, alternate: t.Optional[terms.Term] = None,
) -> terms.Term:
    return terms.sequence(
        "while", condition, "do", body, "else", alternate or create_pass()
    )


def create_while_condition_container(
    condition: terms.Term, loop: terms.Term
) -> terms.Term:
    return terms.sequence("[", condition, "]c", loop)


def create_while_body_container(body: terms.Term, loop: terms.Term) -> terms.Term:
    return terms.sequence("[", body, "]b", loop)


def create_while(
    condition: terms.Term, body: terms.Term, alternate: t.Optional[terms.Term] = None,
) -> terms.Term:
    return create_while_condition_container(
        condition, create_while_loop(condition, body, alternate)
    )


def create_break() -> terms.Term:
    return terms.symbol("break")


def create_continue() -> terms.Term:
    return terms.symbol("continue")


def create_try_finally(body: terms.Term, final: terms.Term) -> terms.Term:
    return terms.sequence("try", body, "finally", final)


def create_finally_container(body: terms.Term, action: terms.Term) -> terms.Term:
    return terms.sequence("[", body, "]f", ".", action)


def create_try_except(
    body: terms.Term, handler: terms.Term, alternative: terms.Term
) -> terms.Term:
    return terms.sequence("try", body, "except", handler, "else", alternative)


def create_except_container(body: terms.Term, exception: terms.Term) -> terms.Term:
    return terms.sequence("[", body, "]e", exception)


def create_get_active_exc() -> terms.Term:
    return terms.symbol("get_active_exc")


def create_return(value: terms.Term) -> terms.Term:
    return terms.sequence("return", value)


def create_print(value: terms.Term) -> terms.Term:
    return terms.sequence("print", value)


def create_sequence(first: terms.Term, second: terms.Term) -> terms.Term:
    return terms.sequence(first, ";", second)


def create_mem_new(value: terms.Term) -> terms.Term:
    return terms.sequence("mem_new", value)


def create_bool(operand: terms.Term) -> terms.Term:
    return terms.sequence("bool", operand)


def create_ternary(
    condition: terms.Term, consequence: terms.Term, alternative: terms.Term
) -> terms.Term:
    return terms.sequence(condition, "?", consequence, ":", alternative)


def create_runtime(name: terms.Term, arguments: terms.Term) -> terms.Term:
    return terms.sequence("runtime", name, arguments)


def create_return_point() -> terms.Term:
    return terms.sequence("entry", ".")


def runtime(name: str, *arguments: terms.Term) -> terms.Term:
    return create_runtime(strings.create(name), create_primitive_list(arguments))


def create_apply(name: terms.Term, arguments: terms.Term) -> terms.Term:
    return terms.sequence("apply", name, arguments)


def apply(name: str, *arguments: terms.Term) -> terms.Term:
    return create_apply(strings.create(name), create_primitive_list(arguments))


def create_send_value(frame: terms.Term, value: terms.Term) -> terms.Term:
    return terms.sequence("send_value", frame, value)


def create_send_throw(frame: terms.Term, value: terms.Term) -> terms.Term:
    return terms.sequence("send_throw", frame, value)


def create_send_entry() -> terms.Term:
    return terms.sequence("send", ".")
