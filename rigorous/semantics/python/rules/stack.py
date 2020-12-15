# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

from ....core import terms
from ....data import booleans
from ....pretty import define

from ... import sos

from . import actions, frames


STACK_NIL = terms.symbol("nil")


def create_stack_cons(frame: terms.Term, tail: terms.Term) -> terms.Term:
    return terms.sequence(tail, "::", frame)


def initialize_stack(frame: terms.Term) -> terms.Term:
    return create_stack_layer(create_stack_cons(frame, STACK_NIL))


def create_stack_layer(stack: terms.Term) -> terms.Term:
    return terms.sequence("stack", stack)


rules = define.group("stack")


var_action = define.variable("action", text="α", math="\\alpha")

var_source = define.variable("source", text="s", math="s")
var_target = define.variable("target", text="t", math="t")

var_other_source = define.variable("source", text="s'", math="s'")
var_other_target = define.variable("target", text="t'", math="t'")

var_frame = define.variable("frame", text="F", math="\\mathfrak{F}")

var_value = define.variable("value", text="v", math="v")
var_tail = define.variable("tail", text="xs", math="xs")


rules.define_rule(
    name="stack-nop",
    premises=(
        sos.transition(source=var_source, action=var_action, target=var_target,),
    ),
    conditions=(booleans.check(booleans.lnot(actions.is_stack_action(var_action))),),
    conclusion=sos.transition(
        source=create_stack_layer(create_stack_cons(var_source, var_tail)),
        action=var_action,
        target=create_stack_layer(create_stack_cons(var_target, var_tail)),
    ),
)

rules.define_rule(
    name="stack-call",
    premises=(
        sos.transition(
            source=var_source, action=actions.create_call(var_frame), target=var_target,
        ),
    ),
    conclusion=sos.transition(
        source=create_stack_layer(create_stack_cons(var_source, var_tail)),
        action=sos.ACTION_TAU,
        target=create_stack_layer(
            create_stack_cons(
                frames.create_frame_layer(var_frame),
                create_stack_cons(var_target, var_tail),
            )
        ),
    ),
)

rules.define_rule(
    name="stack-return",
    premises=(
        sos.transition(
            source=var_source,
            action=actions.create_return(var_value),
            target=var_target,
        ),
        sos.transition(
            source=var_other_source,
            action=actions.create_result(var_value),
            target=var_other_target,
        ),
    ),
    conclusion=sos.transition(
        source=create_stack_layer(
            create_stack_cons(var_source, create_stack_cons(var_other_source, var_tail))
        ),
        action=sos.ACTION_TAU,
        target=create_stack_layer(create_stack_cons(var_other_target, var_tail)),
    ),
)

rules.define_rule(
    name="stack-throw",
    premises=(
        sos.transition(
            source=var_source,
            action=actions.create_throw(var_value),
            target=var_target,
        ),
        sos.transition(
            source=var_other_source,
            action=actions.create_error(var_value),
            target=var_other_target,
        ),
    ),
    conclusion=sos.transition(
        source=create_stack_layer(
            create_stack_cons(var_source, create_stack_cons(var_other_source, var_tail))
        ),
        action=sos.ACTION_TAU,
        target=create_stack_layer(create_stack_cons(var_other_target, var_tail)),
    ),
)

rules.define_rule(
    name="stack-error",
    premises=(
        sos.transition(
            source=var_source,
            action=actions.create_throw(var_value),
            target=var_target,
        ),
    ),
    conclusion=sos.transition(
        source=create_stack_layer(create_stack_cons(var_source, STACK_NIL)),
        action=actions.create_throw(var_value),
        target=create_stack_layer(STACK_NIL),
    ),
)

rules.define_rule(
    name="stack-result",
    premises=(
        sos.transition(
            source=var_source,
            action=actions.create_return(var_value),
            target=var_target,
        ),
    ),
    conclusion=sos.transition(
        source=create_stack_layer(create_stack_cons(var_source, STACK_NIL)),
        action=actions.create_return(var_value),
        target=create_stack_layer(STACK_NIL),
    ),
)

rules.define_rule(
    name="stack-yield",
    premises=(
        sos.transition(
            source=var_source,
            action=actions.create_yield(var_value),
            target=frames.create_frame_layer(var_target),
        ),
        sos.transition(
            source=var_other_source,
            action=actions.create_value(var_target, var_value),
            target=var_other_target,
        ),
    ),
    conclusion=sos.transition(
        source=create_stack_layer(
            create_stack_cons(var_source, create_stack_cons(var_other_source, var_tail))
        ),
        action=sos.ACTION_TAU,
        target=create_stack_layer(create_stack_cons(var_other_target, var_tail)),
    ),
)

rules.define_rule(
    name="stack-send-value",
    premises=(
        sos.transition(
            source=var_source,
            action=actions.create_send_value(var_frame, var_value),
            target=var_target,
        ),
        sos.transition(
            source=frames.create_frame_layer(var_frame),
            action=actions.create_result(var_value),
            target=var_other_target,
        ),
    ),
    conclusion=sos.transition(
        source=create_stack_layer(create_stack_cons(var_source, var_tail)),
        action=sos.ACTION_TAU,
        target=create_stack_layer(
            create_stack_cons(
                var_other_target, create_stack_cons(var_target, var_tail),
            )
        ),
    ),
)

rules.define_rule(
    name="stack-send-error",
    premises=(
        sos.transition(
            source=var_source,
            action=actions.create_send_throw(var_frame, var_value),
            target=var_target,
        ),
        sos.transition(
            source=frames.create_frame_layer(var_frame),
            action=actions.create_error(var_value),
            target=var_other_target,
        ),
    ),
    conclusion=sos.transition(
        source=create_stack_layer(create_stack_cons(var_source, var_tail)),
        action=sos.ACTION_TAU,
        target=create_stack_layer(
            create_stack_cons(
                var_other_target, create_stack_cons(var_target, var_tail),
            )
        ),
    ),
)
