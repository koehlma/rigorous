# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import typing as t

from ....core import terms
from ....data import (
    booleans,
    null,
    numbers,
    references,
    sets,
    tuples,
    records,
    strings,
)
from ....pretty import define

from ... import sos

from ..syntax import operators
from ..basis import primitives

from .. import factory, heap, runtime

from . import actions


rules = define.group("expressions")


var_action = define.variable("action", text="α", math="\\alpha")

var_identifier = define.variable("identifier", text="id", math="\\mathit{id}")
var_name = define.variable("name", text="n", math="\\texttt{n}")
var_reference = define.variable("reference", text="r", math="r")
var_boolean = define.variable("boolean", text="b", math="b")
var_condition = define.variable("condition", text="c", math="c")
var_consequence = define.variable("consequence", text="ec", math="e_c")
var_alternative = define.variable("alternative", text="ea", math="e_a")

var_expression = define.variable("expression", text="e", math="e")
var_expression_left = define.variable("expression_left", text="el", math="e_l")
var_expression_right = define.variable("expression_right", text="er", math="e_r")

var_result = define.variable("result", text="u", math="u")

var_value = define.variable("value", text="v", math="v")
var_value_left = define.variable("value_left", text="vl", math="v_l")
var_value_right = define.variable("value_right", text="vr", math="v_r")

var_default = define.variable("default", text="d", math="d")

var_binary_operator = define.variable("binary_operator", text=" ○ ", math="\\circ")

var_comparison_operator = define.variable(
    "comparison_operator", text=" • ", math="\\bullet"
)
var_comparison_operator_outer = define.variable(
    "comparison_operator_outer", text=" •o ", math="\\bullet_o"
)
var_comparison_operator_inner = define.variable(
    "comparison_operator_inner", text=" •i ", math="\\bullet_i"
)

var_head = define.variable("head", text="x", math="x")
var_tail = define.variable("tail", text="xs", math="xs")

var_frame = define.variable("frame", text="F", math="\\mathfrak{F}")


# region: Primitive Building Blocks

rules.define_rule(
    name="head-eval",
    premises=(
        sos.transition(source=var_expression, action=var_action, target=var_result),
    ),
    conclusion=sos.transition(
        source=factory.create_primitive_cons(var_expression, var_tail),
        action=var_action,
        target=factory.create_primitive_cons(var_result, var_tail),
    ),
)

rules.define_rule(
    name="tail-eval",
    conditions=(booleans.check(booleans.is_primitive(var_head)),),
    premises=(
        sos.transition(source=var_expression, action=var_action, target=var_result),
    ),
    conclusion=sos.transition(
        source=factory.create_primitive_cons(var_head, var_expression),
        action=var_action,
        target=factory.create_primitive_cons(var_head, var_result),
    ),
)

rules.define_rule(
    name="prepend",
    conditions=(
        booleans.check(booleans.is_primitive(var_value_left)),
        booleans.check(booleans.is_primitive(var_value_right)),
    ),
    conclusion=sos.transition(
        source=factory.create_primitive_cons(var_value_left, var_value_right),
        action=sos.ACTION_TAU,
        target=tuples.push_left(var_value_right, var_value_left),
    ),
)

rules.define_rule(
    name="apply-eval",
    premises=(
        sos.transition(source=var_expression, action=var_action, target=var_result),
    ),
    conclusion=sos.transition(
        source=factory.create_apply(var_name, var_expression),
        action=var_action,
        target=factory.create_apply(var_name, var_result),
    ),
)

rules.define_rule(
    name="apply-exec",
    conditions=(booleans.check(booleans.is_primitive(var_value)),),
    conclusion=sos.transition(
        source=factory.create_apply(var_name, var_value),
        action=sos.ACTION_TAU,
        target=primitives.apply(var_name, var_value),
    ),
)

rules.define_rule(
    name="runtime-eval",
    premises=(
        sos.transition(source=var_expression, action=var_action, target=var_result),
    ),
    conclusion=sos.transition(
        source=factory.create_runtime(var_name, var_expression),
        action=var_action,
        target=factory.create_runtime(var_name, var_result),
    ),
)

rules.define_rule(
    name="runtime-exec",
    conditions=(booleans.check(booleans.is_primitive(var_value)),),
    conclusion=sos.transition(
        source=factory.create_runtime(var_name, var_value),
        action=actions.create_call(runtime.make_runtime_frame(var_name, var_value)),
        target=factory.create_return_point(),
    ),
)

rules.define_rule(
    name="entry-result",
    conclusion=sos.transition(
        source=factory.create_return_point(),
        action=actions.create_result(var_value),
        target=var_value,
    ),
)

rules.define_rule(
    name="entry-error",
    conclusion=sos.transition(
        source=factory.create_return_point(),
        action=actions.create_error(var_value),
        target=factory.create_raise(var_value),
    ),
)

# endregion


# region: Local Variables

rules.define_rule(
    name="load-local",
    constraints=(
        (
            var_result,
            booleans.ite(
                booleans.equals(var_value, null.NULL),
                factory.runtime("unbound_local_error", var_identifier),
                var_value,
            ),
        ),
    ),
    conclusion=sos.transition(
        source=factory.create_load_local(var_identifier, var_default),
        action=actions.create_load_local(var_identifier, var_value, var_default),
        target=var_result,
    ),
)

rules.define_rule(
    name="store-local-eval",
    premises=(
        sos.transition(source=var_expression, action=var_action, target=var_result),
    ),
    conclusion=sos.transition(
        source=factory.create_store_local(var_identifier, var_expression),
        action=var_action,
        target=factory.create_store_local(var_identifier, var_result),
    ),
)

rules.define_rule(
    name="store-local-exec",
    conditions=(booleans.check(booleans.is_primitive(var_value)),),
    conclusion=sos.transition(
        source=factory.create_store_local(var_identifier, var_value),
        action=actions.create_store_local(var_identifier, var_value),
        target=var_value,
    ),
)

rules.define_rule(
    name="delete-local",
    constraints=(
        (
            var_result,
            booleans.ite(
                booleans.equals(var_value, null.NULL),
                factory.runtime("unbound_local_error", var_identifier),
                var_value,
            ),
        ),
    ),
    conclusion=sos.transition(
        source=factory.create_delete_local(var_identifier),
        action=actions.create_delete_local(var_identifier, var_value),
        target=var_result,
    ),
)

# endregion


# region: Boolean Operators

rules.define_rule(
    name="bool-eval",
    premises=(
        sos.transition(source=var_expression, action=var_action, target=var_result),
    ),
    conclusion=sos.transition(
        source=factory.create_bool(var_expression),
        action=var_action,
        target=factory.create_bool(var_result),
    ),
)

rules.define_rule(
    name="bool-exec",
    conditions=(
        booleans.check(references.is_reference(var_value)),
        booleans.check(
            sets.not_contains(
                sets.create({heap.TRUE, heap.FALSE, heap.NONE}), var_value
            )
        ),
    ),
    conclusion=sos.transition(
        source=factory.create_bool(var_value),
        action=sos.ACTION_TAU,
        target=factory.create_bool(factory.runtime("convert_bool", var_value)),
    ),
)

rules.define_rule(
    name="bool-true",
    conditions=(
        booleans.check(
            sets.contains(sets.create({booleans.TRUE, heap.TRUE}), var_boolean)
        ),
    ),
    conclusion=sos.transition(
        source=factory.create_bool(var_boolean),
        action=sos.ACTION_TAU,
        target=booleans.TRUE,
    ),
)

rules.define_rule(
    name="bool-false",
    conditions=(
        booleans.check(
            sets.contains(
                sets.create({booleans.FALSE, heap.FALSE, heap.NONE}), var_boolean,
            )
        ),
    ),
    conclusion=sos.transition(
        source=factory.create_bool(var_boolean),
        action=sos.ACTION_TAU,
        target=booleans.FALSE,
    ),
)

rules.define_rule(
    name="ternary-eval",
    premises=(
        sos.transition(source=var_condition, action=var_action, target=var_result),
    ),
    conclusion=sos.transition(
        source=factory.create_ternary(var_condition, var_consequence, var_alternative),
        action=var_action,
        target=factory.create_ternary(var_result, var_consequence, var_alternative),
    ),
)

rules.define_rule(
    name="ternary-true",
    conclusion=sos.transition(
        source=factory.create_ternary(booleans.TRUE, var_consequence, var_alternative),
        action=sos.ACTION_TAU,
        target=var_consequence,
    ),
)

rules.define_rule(
    name="ternary-false",
    conclusion=sos.transition(
        source=factory.create_ternary(booleans.FALSE, var_consequence, var_alternative),
        action=sos.ACTION_TAU,
        target=var_alternative,
    ),
)

rules.define_rule(
    name="bool-left-eval",
    conditions=(
        booleans.check(
            sets.contains(
                sets.create(
                    {
                        terms.symbol(operators.BooleanOperator.AND.symbol),
                        terms.symbol(operators.BooleanOperator.OR.symbol),
                    }
                ),
                var_binary_operator,
            )
        ),
    ),
    premises=(
        sos.transition(
            source=var_expression_left, action=var_action, target=var_result
        ),
    ),
    conclusion=sos.transition(
        source=factory.create_binary(
            var_expression_left, var_binary_operator, var_expression_right
        ),
        action=var_action,
        target=factory.create_binary(
            var_result, var_binary_operator, var_expression_right
        ),
    ),
)

rules.define_rule(
    name="bool-and-exec",
    conditions=(booleans.check(booleans.is_primitive(var_value_left)),),
    conclusion=sos.transition(
        source=factory.create_binary(
            var_value_left, operators.BooleanOperator.AND, var_expression_right
        ),
        action=sos.ACTION_TAU,
        target=factory.create_ternary(
            factory.create_bool(var_value_left), var_expression_right, var_value_left,
        ),
    ),
)

rules.define_rule(
    name="bool-or-exec",
    conditions=(booleans.check(booleans.is_primitive(var_value_left)),),
    conclusion=sos.transition(
        source=factory.create_binary(
            var_value_left, operators.BooleanOperator.OR, var_expression_right
        ),
        action=sos.ACTION_TAU,
        target=factory.create_ternary(
            factory.create_bool(var_value_left), var_value_left, var_expression_right,
        ),
    ),
)

# endregion


# region: Comparison Operators

_COMPARISON_SYMBOLS = {operator.symbol for operator in operators.ComparisonOperator}


@terms.function_operator
def is_comparison_operator(operator: terms.Symbol) -> booleans.Boolean:
    return booleans.create(operator.symbol in _COMPARISON_SYMBOLS)


rules.define_rule(
    name="cmp-left-eval",
    premises=(
        sos.transition(
            source=var_expression_left, action=var_action, target=var_result
        ),
    ),
    conclusion=sos.transition(
        source=factory.create_compare(
            factory.create_binary(
                var_expression_left, var_comparison_operator, var_tail
            )
        ),
        action=var_action,
        target=factory.create_compare(
            factory.create_binary(var_result, var_comparison_operator, var_tail)
        ),
    ),
)

rules.define_rule(
    name="cmp-right-eval1",
    conditions=(booleans.check(booleans.is_primitive(var_value_left)),),
    premises=(
        sos.transition(
            source=var_expression_right, action=var_action, target=var_result
        ),
    ),
    conclusion=sos.transition(
        source=factory.create_compare(
            factory.create_binary(
                var_value_left, var_comparison_operator, var_expression_right
            )
        ),
        action=var_action,
        target=factory.create_compare(
            factory.create_binary(var_value_left, var_comparison_operator, var_result)
        ),
    ),
)

rules.define_rule(
    name="cmp-right-eval2",
    conditions=(
        booleans.check(booleans.is_primitive(var_value_left)),
        booleans.check(is_comparison_operator(var_comparison_operator_inner)),
    ),
    premises=(
        sos.transition(
            source=var_expression_right, action=var_action, target=var_result
        ),
    ),
    conclusion=sos.transition(
        source=factory.create_compare(
            factory.create_binary(
                var_value_left,
                var_comparison_operator_outer,
                factory.create_binary(
                    var_expression_right, var_comparison_operator_inner, var_tail,
                ),
            )
        ),
        action=var_action,
        target=factory.create_compare(
            factory.create_binary(
                var_value_left,
                var_comparison_operator_outer,
                factory.create_binary(
                    var_result, var_comparison_operator_inner, var_tail
                ),
            )
        ),
    ),
)


@terms.function_operator
def compare(
    operator: terms.Symbol, left: terms.Value, right: terms.Value
) -> t.Optional[terms.Term]:
    if operator.symbol == "is":
        return heap.TRUE if left == right else heap.FALSE
    elif operator.symbol == "is not":
        return heap.TRUE if left != right else heap.FALSE
    if isinstance(left, numbers.Number) and isinstance(right, numbers.Number):
        if operator.symbol == "<":
            return heap.TRUE if left.value < right.value else heap.FALSE
        elif operator.symbol == "<=":
            return heap.TRUE if left.value <= right.value else heap.FALSE
        elif operator.symbol == ">=":
            return heap.TRUE if left.value >= right.value else heap.FALSE
        elif operator.symbol == ">":
            return heap.TRUE if left.value > right.value else heap.FALSE
        elif operator.symbol == "==":
            return heap.TRUE if left.value == right.value else heap.FALSE
        elif operator.symbol == "!=":
            return heap.TRUE if left.value != right.value else heap.FALSE
    elif isinstance(left, strings.String) and isinstance(right, strings.String):
        if operator.symbol == "<":
            return heap.TRUE if left.value < right.value else heap.FALSE
        elif operator.symbol == "<=":
            return heap.TRUE if left.value <= right.value else heap.FALSE
        elif operator.symbol == ">=":
            return heap.TRUE if left.value >= right.value else heap.FALSE
        elif operator.symbol == ">":
            return heap.TRUE if left.value > right.value else heap.FALSE
        elif operator.symbol == "==":
            return heap.TRUE if left.value == right.value else heap.FALSE
        elif operator.symbol == "!=":
            return heap.TRUE if left.value != right.value else heap.FALSE
    return factory.runtime(runtime.COMPARE_FUNCTIONS[operator.symbol], left, right)


rules.define_rule(
    name="cmp-exec1",
    conditions=(
        booleans.check(booleans.is_primitive(var_value_left)),
        booleans.check(booleans.is_primitive(var_value_right)),
    ),
    conclusion=sos.transition(
        source=factory.create_compare(
            factory.create_binary(
                var_value_left, var_comparison_operator, var_value_right
            )
        ),
        action=sos.ACTION_TAU,
        target=compare(var_comparison_operator, var_value_left, var_value_right),
    ),
)

rules.define_rule(
    name="cmp-exec2",
    conditions=(
        booleans.check(booleans.is_primitive(var_value_left)),
        booleans.check(booleans.is_primitive(var_value_right)),
        booleans.check(is_comparison_operator(var_comparison_operator_inner)),
    ),
    conclusion=sos.transition(
        source=factory.create_compare(
            factory.create_binary(
                var_value_left,
                var_comparison_operator_outer,
                factory.create_binary(
                    var_value_right, var_comparison_operator_inner, var_tail
                ),
            )
        ),
        action=sos.ACTION_TAU,
        target=factory.create_ternary(
            factory.create_bool(
                compare(var_comparison_operator_outer, var_value_left, var_value_right,)
            ),
            factory.create_compare(
                factory.create_binary(
                    var_value_right, var_comparison_operator_inner, var_tail
                )
            ),
            heap.FALSE,
        ),
    ),
)

# endregion


# region: Call Expression

rules.define_rule(
    name="call-eval",
    premises=(
        sos.transition(source=var_expression, action=var_action, target=var_result),
    ),
    conclusion=sos.transition(
        source=factory.create_call(var_expression),
        action=var_action,
        target=factory.create_call(var_result),
    ),
)

rules.define_rule(
    name="call-exec",
    conditions=(booleans.check(booleans.is_primitive(var_value)),),
    conclusion=sos.transition(
        source=factory.create_call(var_value),
        action=actions.create_call(var_value),
        target=factory.create_return_point(),
    ),
)

# endregion


# region: Yield Expression

rules.define_rule(
    name="yield-eval",
    premises=(
        sos.transition(source=var_expression, action=var_action, target=var_result),
    ),
    conclusion=sos.transition(
        source=factory.create_yield(var_expression),
        action=var_action,
        target=factory.create_yield(var_result),
    ),
)

rules.define_rule(
    name="yield-exec",
    conditions=(booleans.check(booleans.is_primitive(var_value)),),
    conclusion=sos.transition(
        source=factory.create_yield(var_value),
        action=actions.create_yield(var_value),
        target=factory.create_return_point(),
    ),
)

rules.define_rule(
    name="send-value",
    conclusion=sos.transition(
        source=factory.create_send_value(var_frame, var_value),
        action=actions.create_send_value(var_frame, var_value),
        target=factory.create_send_entry(),
    ),
)

rules.define_rule(
    name="send-throw",
    conclusion=sos.transition(
        source=factory.create_send_throw(var_frame, var_value),
        action=actions.create_send_throw(var_frame, var_value),
        target=factory.create_send_entry(),
    ),
)

rules.define_rule(
    name="send-res-error",
    conclusion=sos.transition(
        source=factory.create_send_entry(),
        action=actions.create_error(var_value),
        target=factory.create_raise(var_value),
    ),
)

rules.define_rule(
    name="send-res-result",
    conclusion=sos.transition(
        source=factory.create_send_entry(),
        action=actions.create_result(var_value),
        target=records.construct(
            strings.create("frame"), heap.NONE, strings.create("value"), var_value,
        ),
    ),
)

rules.define_rule(
    name="send-res-value",
    conclusion=sos.transition(
        source=factory.create_send_entry(),
        action=actions.create_value(var_frame, var_value),
        target=records.construct(
            strings.create("frame"), var_frame, strings.create("value"), var_value,
        ),
    ),
)


# endregion


# region: Memory Operations

rules.define_rule(
    name="mem-load-eval",
    premises=(
        sos.transition(source=var_expression, action=var_action, target=var_result),
    ),
    conclusion=sos.transition(
        source=factory.create_mem_load(var_expression),
        action=var_action,
        target=factory.create_mem_load(var_result),
    ),
)

rules.define_rule(
    name="mem-load-exec",
    conditions=(booleans.check(booleans.is_primitive(var_reference)),),
    conclusion=sos.transition(
        source=factory.create_mem_load(var_reference),
        action=actions.create_mem_load(var_reference, var_value),
        target=var_value,
    ),
)

rules.define_rule(
    name="mem-new-eval",
    premises=(
        sos.transition(source=var_expression, action=var_action, target=var_result),
    ),
    conclusion=sos.transition(
        source=factory.create_mem_new(var_expression),
        action=var_action,
        target=factory.create_mem_new(var_result),
    ),
)

rules.define_rule(
    name="mem-new-exec",
    conditions=(booleans.check(booleans.is_primitive(var_value)),),
    conclusion=sos.transition(
        source=factory.create_mem_new(var_value),
        action=actions.create_mem_new(var_reference, var_value),
        target=var_reference,
    ),
)

rules.define_rule(
    name="mem-store-eval1",
    premises=(
        sos.transition(source=var_reference, action=var_action, target=var_result),
    ),
    conclusion=sos.transition(
        source=factory.create_mem_store(var_reference, var_expression),
        action=var_action,
        target=factory.create_mem_store(var_result, var_expression),
    ),
)

rules.define_rule(
    name="mem-store-eval2",
    conditions=(booleans.check(booleans.is_primitive(var_reference)),),
    premises=(
        sos.transition(source=var_expression, action=var_action, target=var_result),
    ),
    conclusion=sos.transition(
        source=factory.create_mem_store(var_reference, var_expression),
        action=var_action,
        target=factory.create_mem_store(var_reference, var_result),
    ),
)

rules.define_rule(
    name="mem-store-exec",
    conditions=(
        booleans.check(booleans.is_primitive(var_reference)),
        booleans.check(booleans.is_primitive(var_value)),
    ),
    conclusion=sos.transition(
        source=factory.create_mem_store(var_reference, var_value),
        action=actions.create_mem_store(var_reference, var_value),
        target=var_reference,
    ),
)

# endregion


# region: Primitive Print

rules.define_rule(
    name="print-eval",
    premises=(
        sos.transition(source=var_expression, action=var_action, target=var_result,),
    ),
    conclusion=sos.transition(
        source=factory.create_print(var_expression),
        action=var_action,
        target=factory.create_print(var_result),
    ),
)

rules.define_rule(
    name="print-exec",
    conditions=(booleans.check(booleans.is_primitive(var_value)),),
    conclusion=sos.transition(
        source=factory.create_print(var_value),
        action=actions.create_print(var_value),
        target=var_value,
    ),
)

# endregion
