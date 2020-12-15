# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

from ....core import terms
from ....data import booleans, mappings, references
from ....pretty import define

from ... import sos

from . import actions


def create_memory_layer(memory: terms.Term, process: terms.Term) -> terms.Term:
    return terms.sequence("memory", memory, ":", process)


rules = define.group("memory")


var_action = define.variable("action", text="α", math="\\alpha")

var_source = define.variable("source", text="s", math="s")
var_target = define.variable("target", text="t", math="t")

var_heap = define.variable("heap", text="H", math="\\mathcal{H}")

var_other_heap = define.variable("other_heap", text="H'", math="\\mathcal{H}'")

var_reference = define.variable("reference", text="r", math="r")
var_value = define.variable("value", text="v", math="v")


rules.define_rule(
    name="mem-nop",
    premises=(
        sos.transition(source=var_source, action=var_action, target=var_target,),
    ),
    conditions=(booleans.check(booleans.lnot(actions.is_memory_action(var_action))),),
    conclusion=sos.transition(
        source=create_memory_layer(var_heap, var_source),
        action=var_action,
        target=create_memory_layer(var_heap, var_target),
    ),
)

rules.define_rule(
    name="mem-load",
    premises=(
        sos.transition(
            source=var_source,
            action=actions.create_mem_load(
                var_reference, mappings.getitem(var_heap, var_reference)
            ),
            target=var_target,
        ),
    ),
    conclusion=sos.transition(
        source=create_memory_layer(var_heap, var_source),
        action=sos.ACTION_TAU,
        target=create_memory_layer(var_heap, var_target),
    ),
)

rules.define_rule(
    name="mem-store",
    premises=(
        sos.transition(
            source=var_source,
            action=actions.create_mem_store(var_reference, var_value),
            target=var_target,
        ),
    ),
    conclusion=sos.transition(
        source=create_memory_layer(var_heap, var_source),
        action=sos.ACTION_TAU,
        target=create_memory_layer(
            references.store(var_heap, var_reference, var_value), var_target
        ),
    ),
)

rules.define_rule(
    name="mem-new",
    premises=(
        sos.transition(
            source=var_source,
            action=actions.create_mem_new(var_reference, var_value),
            target=var_target,
        ),
    ),
    constraints=(
        (
            references.create_new_result(var_other_heap, var_reference),
            references.new(var_heap, var_value),
        ),
    ),
    conclusion=sos.transition(
        source=create_memory_layer(var_heap, var_source),
        action=sos.ACTION_TAU,
        target=create_memory_layer(var_other_heap, var_target),
    ),
)
