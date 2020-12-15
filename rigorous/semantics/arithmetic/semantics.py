# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>
#
# fmt: off

from __future__ import annotations

from ...core import inference, terms
from ...data import booleans, numbers, sets
from ...pretty import define

from .. import sos


BINARY_ADD = terms.symbol("+")
BINARY_SUB = terms.symbol("-")
BINARY_MUL = terms.symbol("*")
BINARY_DIV = terms.symbol("/")

BINARY_OPERATORS = sets.create({BINARY_ADD, BINARY_SUB, BINARY_MUL, BINARY_DIV})


def is_binary_operator(operator: terms.Term) -> inference.Condition:
    return booleans.check(sets.contains(BINARY_OPERATORS, operator))


left_expr = define.variable("left_expr", text="el", math="e_l")
right_expr = define.variable("right_expr", text="er", math="e_r")

left_int = define.variable("left_int", text="zl", math="z_l")
right_int = define.variable("right_int", text="zr", math="z_r")

some_result = define.variable("result", text="u", math="u")

some_operator = define.variable("operator", text="○", math="\\circ")


def binary_expr(
    left: terms.Term, operator: terms.Term, right: terms.Term
) -> terms.Term:
    return terms.sequence(left, operator, right)


l_eval_rule = define.rule(
    name="l-eval",
    premises=(
        sos.transition(
            source=left_expr, action=sos.some_action, target=some_result
        ),
    ),
    conditions=(is_binary_operator(some_operator),),
    conclusion=sos.transition(
        source=binary_expr(left_expr, some_operator, right_expr),
        action=sos.some_action,
        target=binary_expr(some_result, some_operator, right_expr),
    ),
)

r_eval_rule = define.rule(
    name="r-eval",
    premises=(
        sos.transition(
            source=right_expr, action=sos.some_action, target=some_result
        ),
    ),
    conditions=(is_binary_operator(some_operator),),
    conclusion=sos.transition(
        source=binary_expr(left_expr, some_operator, right_expr),
        action=sos.some_action,
        target=binary_expr(left_expr, some_operator, some_result),
    ),
)

add_eval_rule = define.rule(
    name="add-eval",
    conclusion=sos.transition(
        source=binary_expr(left_int, BINARY_ADD, right_int),
        action=sos.ACTION_TAU,
        target=numbers.add(left_int, right_int),
    ),
)

sub_eval_rule = define.rule(
    name="sub-eval",
    conclusion=sos.transition(
        source=binary_expr(left_int, BINARY_SUB, right_int),
        action=sos.ACTION_TAU,
        target=numbers.sub(left_int, right_int),
    ),
)

mul_eval_rule = define.rule(
    name="mul-eval",
    conclusion=sos.transition(
        source=binary_expr(left_int, BINARY_MUL, right_int),
        action=sos.ACTION_TAU,
        target=numbers.mul(left_int, right_int),
    ),
)

div_eval_rule = define.rule(
    name="div-eval",
    conclusion=sos.transition(
        source=binary_expr(left_int, BINARY_DIV, right_int),
        action=sos.ACTION_TAU,
        target=numbers.floor_div(left_int, right_int),
    ),
)

system = inference.System(
    [
        l_eval_rule,
        r_eval_rule,
        add_eval_rule,
        sub_eval_rule,
        mul_eval_rule,
        div_eval_rule,
    ]
)
