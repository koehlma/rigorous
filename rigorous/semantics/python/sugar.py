# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import typing as t

from ...core import terms
from ...data import strings
from ...pretty import define

from .syntax import operators

from . import heap, factory


def create_load_global(identifier: terms.Term) -> terms.Term:
    return factory.runtime(
        "load_global", factory.create_load_local("__globals__"), identifier,
    )


def create_load_cell(identifier: terms.Term) -> terms.Term:
    return factory.runtime(
        "load_cell", factory.create_load_local("__cells__"), identifier
    )


def create_load_class_global(identifier: terms.Term) -> terms.Term:
    return factory.runtime(
        "load_class_global",
        factory.create_load_local("__dict__"),
        factory.create_load_local("__globals__"),
        identifier,
    )


def create_load_class_cell(identifier: terms.Term) -> terms.Term:
    return factory.runtime(
        "load_class_cell",
        factory.create_load_local("__dict__"),
        factory.create_load_local("__cells__"),
        identifier,
    )


def create_store_global(identifier: terms.Term, value: terms.Term) -> terms.Term:
    return factory.runtime(
        "store_global", factory.create_load_local("__globals__"), identifier, value,
    )


def create_store_cell(identifier: terms.Term, value: terms.Term) -> terms.Term:
    return factory.runtime(
        "store_cell", factory.create_load_local("__cells__"), identifier, value
    )


def create_store_class(identifier: terms.Term, value: terms.Term) -> terms.Term:
    return factory.runtime(
        "store_class", factory.create_load_local("__dict__"), identifier, value
    )


def create_make_list(elements: terms.Term) -> terms.Term:
    return factory.runtime("make_list", elements)


def create_make_tuple(elements: terms.Term) -> terms.Term:
    return factory.runtime("make_tuple", elements)


def create_make_dict(elements: terms.Term) -> terms.Term:
    return factory.runtime("make_dict", elements)


def create_setitem(
    operand: terms.Term, key: terms.Term, value: terms.Term
) -> terms.Term:
    return factory.create_eval(factory.runtime("set_item", operand, key, value))


def create_set_attribute(
    operand: terms.Term, attribute: terms.Term, value: terms.Term
) -> terms.Term:
    return factory.create_eval(
        factory.runtime("set_attribute", operand, attribute, value)
    )


def create_raise(expression: t.Optional[terms.Term] = None) -> terms.Term:
    if expression is None:
        return factory.create_raise(
            factory.runtime("check_active_exception", factory.create_get_active_exc())
        )
    else:
        return factory.create_raise(
            factory.runtime(
                "ensure_exception", expression, factory.create_get_active_exc()
            )
        )


def create_if(
    condition: terms.Term,
    consequent: terms.Term,
    alternate: t.Optional[terms.Term] = None,
) -> terms.Term:
    return factory.create_if(
        factory.create_bool(condition), consequent, alternate or factory.create_pass(),
    )


def create_while(
    condition: terms.Term, body: terms.Term, alternate: terms.Term
) -> terms.Term:
    return factory.create_while(factory.create_bool(condition), body, alternate)


def create_try_finally(body: terms.Term, cleanup: terms.Term) -> terms.Term:
    return factory.create_try_finally(body, cleanup)


def create_eval_getattr(operand: terms.Term, attribute: terms.Term) -> terms.Term:
    return factory.runtime("get_attribute", operand, attribute)


def create_eval_getitem(operand: terms.Term, item: terms.Term) -> terms.Term:
    return factory.runtime("get_item", operand, item)


def create_eval_not(operand: terms.Term) -> terms.Term:
    return factory.create_ternary(factory.create_bool(operand), heap.FALSE, heap.TRUE)


def create_delete_global(identifier: terms.Term) -> terms.Term:
    return factory.create_eval(
        factory.runtime(
            "delete_global", factory.create_load_local("__globals__"), identifier,
        )
    )


def create_delete_cell(identifier: terms.Term) -> terms.Term:
    return factory.create_eval(
        factory.runtime(
            "delete_cell", factory.create_load_local("__cells__"), identifier
        )
    )


def create_delete_class(identifier: terms.Term) -> terms.Term:
    return factory.create_eval(
        factory.runtime(
            "delete_class", factory.create_load_local("__dict__"), identifier
        )
    )


def create_delete_attribute(operand: terms.Term, attribute: terms.Term) -> terms.Term:
    return factory.create_eval(factory.runtime("delete_attribute", operand, attribute))


def create_delete_item(operand: terms.Term, item: terms.Term) -> terms.Term:
    return factory.create_eval(factory.runtime("delete_item", operand, item))


def create_eval_binary(
    operator: operators.BinaryOperator, left: terms.Term, right: terms.Term
) -> terms.Term:
    return factory.runtime(
        "binary_operator",
        left,
        right,
        strings.create(operator.left_slot),
        strings.create(operator.right_slot),
    )


def create_eval_unary(
    operator: operators.UnaryOperator, operand: terms.Term
) -> terms.Term:
    return factory.runtime("unary_operator", operand, strings.create(operator.slot))


def create_keyword_add(
    name: terms.Term, expression: terms.Term, keyword_arguments: terms.Term
) -> terms.Term:
    return factory.apply("mapping_set", keyword_arguments, name, expression,)


def create_unpack_positional(
    expression: terms.Term, positional_arguments: terms.Term,
) -> terms.Term:
    return factory.apply(
        "sequence_concat",
        factory.runtime("unpack_iterable", expression),
        positional_arguments,
    )


def create_unpack_keywords(
    expression: terms.Term, keyword_arguments: terms.Term
) -> terms.Term:
    return factory.apply(
        "mapping_update",
        keyword_arguments,
        factory.runtime("unpack_str_mapping", expression),
    )


def create_call(
    function: terms.Term,
    positional_arguments: terms.Term,
    keyword_arguments: terms.Term,
) -> terms.Term:
    return factory.runtime("call", positional_arguments, keyword_arguments, function)


var_identifier = define.variable("identifier", text="id", math="\\mathit{id}")

var_elements = define.variable("elements", text="els", math="\\mathit{els}")
var_items = define.variable("items", text="its", math="\\mathit{its}")

var_key = define.variable("key", text="ek", math="e_k")
var_value = define.variable("value", text="ev", math="e_v")

var_item = define.variable("item", text="ei", math="e_i")
var_attr = define.variable("attr", text="attr", math="\\mathit{attr}")

var_function = define.variable("function", text="f", math="f")
var_positional_arguments = define.variable(
    "positional_arguments", text="ap", math="\\vec{a}_p"
)
var_keyword_arguments = define.variable(
    "keyword_arguments", text="ak", math="\\vec{a}_k"
)

var_expression = define.variable("expression", text="e", math="e")
var_expression_left = define.variable("expression_left", text="el", math="e_l")
var_expression_right = define.variable("expression_right", text="er", math="e_r")

var_condition = define.variable("condition", text="ec", math="e_c")

var_body = define.variable("body", text="sb", math="s_b")
var_cleanup = define.variable("cleanup", text="sc", math="s_c")

var_consequent = define.variable("consequent", text="sc", math="s_c")
var_alternate = define.variable("alternate", text="sa", math="s_a")


create_set_item = create_setitem


SUGAR = {
    "load-global": create_load_global(var_identifier),
    "load-cell": create_load_cell(var_identifier),
    "load-class-global": create_load_class_global(var_identifier),
    "load-class-cell": create_load_class_cell(var_identifier),
    "make-list": create_make_list(var_elements),
    "make-tuple": create_make_tuple(var_elements),
    "make-dict": create_make_dict(var_items),
    "raise-expression": create_raise(var_expression),
    "raise": create_raise(),
    "if": create_if(var_condition, var_consequent, var_alternate),
    "try-finally": create_try_finally(var_body, var_cleanup),
    "while": create_while(var_condition, var_body, var_alternate),
    # Assignments
    "store-global": create_store_global(var_identifier, var_value),
    "store-cell": create_store_cell(var_identifier, var_value),
    "store-class": create_store_class(var_identifier, var_value),
    "set-attribute": create_set_attribute(var_expression, var_attr, var_value),
    "set-item": create_set_item(var_expression, var_key, var_value),
    # The `del` Statement
    "delete-global": create_delete_global(var_identifier),
    "delete-cell": create_delete_cell(var_identifier),
    "delete-class": create_delete_class(var_identifier),
    "delete-attribute": create_delete_attribute(var_expression, var_attr),
    "delete-item": create_delete_item(var_expression, var_key),
    # ...
    "eval-getattr": create_eval_getattr(var_expression, var_attr),
    "eval-getitem": create_eval_getitem(var_expression, var_item),
    "eval-not": create_eval_not(var_expression),
    "keyword-add": create_keyword_add(
        var_identifier, var_expression, var_keyword_arguments
    ),
    "unpack-positional": create_unpack_positional(
        var_expression, var_positional_arguments
    ),
    "unpack-keywords": create_unpack_keywords(var_expression, var_keyword_arguments),
    "call": create_call(var_function, var_positional_arguments, var_keyword_arguments),
}

SUGAR.update(
    {
        f"binary-{operator.method}": create_eval_binary(
            operator, var_expression_left, var_expression_right
        )
        for operator in operators.BinaryOperator
    }
)

SUGAR.update(
    {
        f"unary-{operator.method}": create_eval_unary(operator, var_expression)
        for operator in operators.UnaryOperator
    }
)
