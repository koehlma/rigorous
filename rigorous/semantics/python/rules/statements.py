# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

from ....core import terms
from ....data import booleans
from ....pretty import define

from ... import sos

from .. import factory

from . import actions


rules = define.group("statement")


DEAD = terms.symbol("⊥")

var_action = define.variable("action", text="α", math="\\alpha")

var_other_action = define.variable("other_action", text="β", math="\\beta")

var_body = define.variable("body", text="sb", math="s_b")
var_final = define.variable("final", text="sc", math="s_c")
var_handler = define.variable("handler", text="sh", math="s_h")

var_source = define.variable("source", text="s", math="s")
var_target = define.variable("target", text="t", math="t")

var_consequence = define.variable("consequence", text="sc", math="s_c")
var_alternative = define.variable("alternative", text="sa", math="s_a")

var_other_source = define.variable("source", text="s'", math="s'")
var_other_target = define.variable("source", text="t'", math="t'")

var_expression = define.variable("expression", text="e", math="e")
var_result = define.variable("result", text="u", math="u")
var_value = define.variable("value", text="v", math="v")

var_loop = define.variable("loop", text="L", math="L")


# region: Sequence Statement

rules.define_rule(
    name="sequence-first",
    premises=(sos.transition(source=var_source, action=var_action, target=var_target),),
    conclusion=sos.transition(
        source=factory.create_sequence(var_source, var_other_source),
        action=var_action,
        target=factory.create_sequence(var_target, var_other_source),
    ),
)

rules.define_rule(
    name="sequence-elim",
    conclusion=sos.transition(
        source=factory.create_sequence(DEAD, var_source),
        action=sos.ACTION_TAU,
        target=var_source,
    ),
)

# endregion


# region: Expression Statement

rules.define_rule(
    name="eval",
    premises=(
        sos.transition(source=var_expression, action=var_action, target=var_result,),
    ),
    conclusion=sos.transition(
        source=factory.create_eval(var_expression),
        action=var_action,
        target=factory.create_eval(var_result),
    ),
)

rules.define_rule(
    name="eval-elim",
    conditions=(booleans.check(booleans.is_primitive(var_value)),),
    conclusion=sos.transition(
        source=factory.create_eval(var_value), action=sos.ACTION_TAU, target=DEAD,
    ),
)

# endregion


# region: Pass Statement

rules.define_rule(
    name="pass",
    conclusion=sos.transition(
        source=factory.create_pass(), action=sos.ACTION_TAU, target=DEAD
    ),
)

# endregion


# region: Return Statement

rules.define_rule(
    name="return-eval",
    premises=(
        sos.transition(source=var_expression, action=var_action, target=var_result,),
    ),
    conclusion=sos.transition(
        source=factory.create_return(var_expression),
        action=var_action,
        target=factory.create_return(var_result),
    ),
)

rules.define_rule(
    name="return-exec",
    conditions=(booleans.check(booleans.is_primitive(var_value)),),
    conclusion=sos.transition(
        source=factory.create_return(var_value),
        action=actions.create_return(var_value),
        target=DEAD,
    ),
)

# endregion


# region: If Statement

rules.define_rule(
    name="if-eval",
    premises=(
        sos.transition(source=var_expression, action=var_action, target=var_result,),
    ),
    conclusion=sos.transition(
        source=factory.create_if(var_expression, var_consequence, var_alternative),
        action=var_action,
        target=factory.create_if(var_result, var_consequence, var_alternative),
    ),
)

rules.define_rule(
    name="if-true",
    conclusion=sos.transition(
        source=factory.create_if(booleans.TRUE, var_consequence, var_alternative),
        action=sos.ACTION_TAU,
        target=var_consequence,
    ),
)

rules.define_rule(
    name="if-false",
    conclusion=sos.transition(
        source=factory.create_if(booleans.FALSE, var_consequence, var_alternative),
        action=sos.ACTION_TAU,
        target=var_alternative,
    ),
)

# endregion


# region: Loop Control Statements

rules.define_rule(
    name="continue",
    conclusion=sos.transition(
        source=factory.create_continue(), action=actions.ACTION_CONTINUE, target=DEAD,
    ),
)

rules.define_rule(
    name="break",
    conclusion=sos.transition(
        source=factory.create_break(), action=actions.ACTION_BREAK, target=DEAD
    ),
)

# endregion


# region: While Statement

rules.define_rule(
    name="while-eval",
    premises=(
        sos.transition(source=var_expression, action=var_action, target=var_result,),
    ),
    conclusion=sos.transition(
        source=factory.create_while_condition_container(var_expression, var_loop),
        action=var_action,
        target=factory.create_while_condition_container(var_result, var_loop),
    ),
)

rules.define_rule(
    name="while-true",
    conclusion=sos.transition(
        source=factory.create_while_condition_container(
            booleans.TRUE,
            factory.create_while_loop(var_expression, var_body, var_alternative),
        ),
        action=sos.ACTION_TAU,
        target=factory.create_while_body_container(
            var_body,
            factory.create_while_loop(var_expression, var_body, var_alternative),
        ),
    ),
)

rules.define_rule(
    name="while-false",
    conclusion=sos.transition(
        source=factory.create_while_condition_container(
            booleans.FALSE,
            factory.create_while_loop(var_expression, var_body, var_alternative),
        ),
        action=sos.ACTION_TAU,
        target=var_alternative,
    ),
)

rules.define_rule(
    name="while-body",
    premises=(
        sos.transition(source=var_source, action=var_action, target=var_target,),
    ),
    conditions=(booleans.check(booleans.lnot(actions.is_loop_action(var_action))),),
    conclusion=sos.transition(
        source=factory.create_while_body_container(var_source, var_loop),
        action=var_action,
        target=factory.create_while_body_container(var_target, var_loop),
    ),
)

rules.define_rule(
    name="while-repeat",
    conclusion=sos.transition(
        source=factory.create_while_body_container(
            DEAD, factory.create_while_loop(var_expression, var_body, var_alternative),
        ),
        action=sos.ACTION_TAU,
        target=factory.create_while_condition_container(
            var_expression,
            factory.create_while_loop(var_expression, var_body, var_alternative),
        ),
    ),
)

rules.define_rule(
    name="while-break",
    premises=(
        sos.transition(
            source=var_source, action=actions.ACTION_BREAK, target=var_target,
        ),
    ),
    conclusion=sos.transition(
        source=factory.create_while_body_container(var_source, var_loop),
        action=sos.ACTION_TAU,
        target=DEAD,
    ),
)

rules.define_rule(
    name="while-continue",
    premises=(
        sos.transition(
            source=var_source, action=actions.ACTION_CONTINUE, target=var_target,
        ),
    ),
    conclusion=sos.transition(
        source=factory.create_while_body_container(
            var_source,
            factory.create_while_loop(var_expression, var_body, var_alternative),
        ),
        action=sos.ACTION_TAU,
        target=factory.create_while_condition_container(
            var_expression,
            factory.create_while_loop(var_expression, var_body, var_alternative),
        ),
    ),
)

# endregion


# region: Raise Statement

rules.define_rule(
    name="raise-eval",
    premises=(
        sos.transition(source=var_expression, action=var_action, target=var_result,),
    ),
    conclusion=sos.transition(
        source=factory.create_raise(var_expression),
        action=var_action,
        target=factory.create_raise(var_result),
    ),
)

rules.define_rule(
    name="raise-exec",
    conditions=(booleans.check(booleans.is_primitive(var_value)),),
    conclusion=sos.transition(
        source=factory.create_raise(var_value),
        action=actions.create_throw(var_value),
        target=DEAD,
    ),
)

rules.define_rule(
    name="get-active-exc",
    conclusion=sos.transition(
        source=factory.create_get_active_exc(),
        action=actions.create_get_active_exc(var_value),
        target=var_value,
    ),
)

# endregion


# region: Try-Finally Statement

rules.define_rule(
    name="finally-body",
    premises=(sos.transition(source=var_source, action=var_action, target=var_target),),
    conditions=(
        booleans.check(booleans.lnot(actions.is_terminating_action(var_action))),
    ),
    conclusion=sos.transition(
        source=factory.create_try_finally(var_source, var_final),
        action=var_action,
        target=factory.create_try_finally(var_target, var_final),
    ),
)

rules.define_rule(
    name="finally-cleanup1",
    premises=(sos.transition(source=var_source, action=var_action, target=var_target),),
    conditions=(booleans.check(actions.is_terminating_action(var_action)),),
    conclusion=sos.transition(
        source=factory.create_try_finally(var_source, var_final),
        action=sos.ACTION_TAU,
        target=factory.create_finally_container(var_final, var_action),
    ),
)

rules.define_rule(
    name="finally-cleanup2",
    conclusion=sos.transition(
        source=factory.create_try_finally(DEAD, var_final),
        action=sos.ACTION_TAU,
        target=var_final,
    ),
)

rules.define_rule(
    name="finally-container",
    premises=(sos.transition(source=var_source, action=var_action, target=var_target),),
    conditions=(
        booleans.check(
            booleans.lor(
                booleans.lnot(actions.is_get_exc_action(var_action)),
                booleans.lnot(actions.is_throw_action(var_other_action)),
            )
        ),
    ),
    conclusion=sos.transition(
        source=factory.create_finally_container(var_source, var_other_action),
        action=var_action,
        target=factory.create_finally_container(var_target, var_other_action),
    ),
)

rules.define_rule(
    name="finally-get-active-exc",
    premises=(
        sos.transition(
            source=var_source,
            action=actions.create_get_active_exc(var_value),
            target=var_target,
        ),
    ),
    conclusion=sos.transition(
        source=factory.create_finally_container(
            var_source, actions.create_throw(var_value)
        ),
        action=sos.ACTION_TAU,
        target=factory.create_finally_container(
            var_target, actions.create_throw(var_value)
        ),
    ),
)

rules.define_rule(
    name="finally-done",
    conclusion=sos.transition(
        source=factory.create_finally_container(DEAD, var_action),
        action=var_action,
        target=DEAD,
    ),
)

# endregion


# region: Try-Except Statement

rules.define_rule(
    name="except-body",
    premises=(sos.transition(source=var_source, action=var_action, target=var_target),),
    conditions=(booleans.check(booleans.lnot(actions.is_throw_action(var_action))),),
    conclusion=sos.transition(
        source=factory.create_try_except(var_source, var_handler, var_alternative),
        action=var_action,
        target=factory.create_try_except(var_target, var_handler, var_alternative),
    ),
)

rules.define_rule(
    name="except-done",
    conclusion=sos.transition(
        source=factory.create_try_except(DEAD, var_handler, var_alternative),
        action=sos.ACTION_TAU,
        target=var_alternative,
    ),
)

rules.define_rule(
    name="except-handle",
    premises=(
        sos.transition(
            source=var_source,
            action=actions.create_throw(var_value),
            target=var_target,
        ),
    ),
    conclusion=sos.transition(
        source=factory.create_try_except(var_source, var_handler, var_alternative),
        action=sos.ACTION_TAU,
        target=factory.create_except_container(var_handler, var_value),
    ),
)

rules.define_rule(
    name="except-get-active-exc",
    premises=(
        sos.transition(
            source=var_source,
            action=actions.create_get_active_exc(var_value),
            target=var_target,
        ),
    ),
    conclusion=sos.transition(
        source=factory.create_except_container(var_source, var_value),
        action=sos.ACTION_TAU,
        target=factory.create_except_container(var_target, var_value),
    ),
)

rules.define_rule(
    name="except-exec",
    premises=(
        sos.transition(source=var_source, action=var_action, target=var_target,),
    ),
    conditions=(booleans.check(booleans.lnot(actions.is_get_exc_action(var_action))),),
    conclusion=sos.transition(
        source=factory.create_except_container(var_source, var_value),
        action=var_action,
        target=factory.create_except_container(var_target, var_value),
    ),
)

rules.define_rule(
    name="except-caught",
    conclusion=sos.transition(
        source=factory.create_except_container(DEAD, var_value),
        action=sos.ACTION_TAU,
        target=DEAD,
    ),
)


# endregion
