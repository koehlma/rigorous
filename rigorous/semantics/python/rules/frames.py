# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

from ....core import terms
from ....data import booleans, mappings, null, records
from ....pretty import define

from ... import sos

from .. import heap

from . import actions


def create_frame_layer(descriptor: terms.Term) -> terms.Term:
    return terms.sequence("frame", descriptor)


rules = define.group("frame")


var_action = define.variable("action", text="α", math="\\alpha")

var_source = define.variable("source", text="s", math="s")
var_target = define.variable("target", text="t", math="t")

var_descriptor = define.variable("descriptor", text="F", math="\\mathfrak{F}")

var_identifier = define.variable("identifier", text="id", math="\\mathit{id}")

var_value = define.variable("value", text="v", math="v")
var_default = define.variable("default", text="d", math="d")


rules.define_rule(
    name="frame-nop",
    premises=(
        sos.transition(
            source=records.getfield(var_descriptor, "body"),
            action=var_action,
            target=var_target,
        ),
    ),
    conditions=(booleans.check(booleans.lnot(actions.is_frame_action(var_action))),),
    conclusion=sos.transition(
        source=create_frame_layer(var_descriptor),
        action=var_action,
        target=create_frame_layer(records.setfield(var_descriptor, "body", var_target)),
    ),
)

rules.define_rule(
    name="frame-no-active-exc",
    premises=(
        sos.transition(
            source=records.getfield(var_descriptor, "body"),
            action=actions.create_get_active_exc(heap.NONE),
            target=var_target,
        ),
    ),
    conclusion=sos.transition(
        source=create_frame_layer(var_descriptor),
        action=sos.ACTION_TAU,
        target=create_frame_layer(records.setfield(var_descriptor, "body", var_target)),
    ),
)

rules.define_rule(
    name="frame-load-local",
    premises=(
        sos.transition(
            source=records.getfield(var_descriptor, "body"),
            action=actions.create_load_local(
                var_identifier,
                mappings.getitem(
                    records.getfield(var_descriptor, "locals"),
                    var_identifier,
                    var_default,
                ),
                var_default,
            ),
            target=var_target,
        ),
    ),
    conclusion=sos.transition(
        source=create_frame_layer(var_descriptor),
        action=sos.ACTION_TAU,
        target=create_frame_layer(records.setfield(var_descriptor, "body", var_target)),
    ),
)

rules.define_rule(
    name="frame-store-local",
    premises=(
        sos.transition(
            source=records.getfield(var_descriptor, "body"),
            action=actions.create_store_local(var_identifier, var_value),
            target=var_target,
        ),
    ),
    conclusion=sos.transition(
        source=create_frame_layer(var_descriptor),
        action=sos.ACTION_TAU,
        target=create_frame_layer(
            records.setfield(
                records.setfield(
                    var_descriptor,
                    "locals",
                    mappings.setitem(
                        records.getfield(var_descriptor, "locals"),
                        var_identifier,
                        var_value,
                    ),
                ),
                "body",
                var_target,
            )
        ),
    ),
)

rules.define_rule(
    name="frame-delete-local",
    premises=(
        sos.transition(
            source=records.getfield(var_descriptor, "body"),
            action=actions.create_delete_local(
                var_identifier,
                mappings.getitem(
                    records.getfield(var_descriptor, "locals"),
                    var_identifier,
                    null.NULL,
                ),
            ),
            target=var_target,
        ),
    ),
    conclusion=sos.transition(
        source=create_frame_layer(var_descriptor),
        action=sos.ACTION_TAU,
        target=create_frame_layer(
            records.setfield(
                records.setfield(
                    var_descriptor,
                    "locals",
                    mappings.delitem(
                        records.getfield(var_descriptor, "locals"), var_identifier,
                    ),
                ),
                "body",
                var_target,
            )
        ),
    ),
)
