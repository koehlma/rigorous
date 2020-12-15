# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import typing as t

from ...core import inference, terms, unification
from ...data import mappings, records, strings

from ..executors.bottom_up import Executor, Transition

from .rules import expressions, frames, memory, stack, statements

from . import heap


system = inference.System()

memory.rules.add_to_system(system)
frames.rules.add_to_system(system)
stack.rules.add_to_system(system)
expressions.rules.add_to_system(system)
statements.rules.add_to_system(system)


def create_executor(*, shortcircuit: bool = True) -> Executor:
    executor = Executor(shortcircuit=shortcircuit)
    for rule in system.rules:
        executor.add_rule(rule)
    return executor


executor = create_executor()


_ACTION_NAME = terms.variable("action_name")
_ACTION_VALUE = terms.variable("action_value")

_ACTION_PATTERN = terms.sequence(_ACTION_NAME, _ACTION_VALUE)


def _unwrap_action(action: terms.Term) -> t.Optional[t.Tuple[str, terms.Term]]:
    match = unification.match(_ACTION_PATTERN, action)
    if match is not None:
        action_name = match[_ACTION_NAME]
        action_value = match[_ACTION_VALUE]
        if isinstance(action_name, terms.Symbol):
            return action_name.symbol, action_value
    return None


def run(body: terms.Term, heap_builder: heap.Builder) -> t.Optional[terms.Term]:
    local_namespace = mappings.create(
        {
            strings.create("__globals__"): heap_builder.new_mapping_proxy(),
            strings.create("__cells__"): mappings.EMPTY,
        }
    )
    initial_state = memory.create_memory_layer(
        heap_builder.heap,
        stack.initialize_stack(
            frames.create_frame_layer(records.create(locals=local_namespace, body=body))
        ),
    )
    for transition in executor.iter_transitions(initial_state):
        action = _unwrap_action(transition.action)
        if action is None:
            print("bad action")
            print(action)
        else:
            action_name, action_value = action
            if action_name == "PRINT":
                if isinstance(action_value, strings.String):
                    print(action_value.value)
                else:
                    print(action_value)
            elif action_name == "THROW":
                raise Exception(action_value)
            elif action_name == "RETURN":
                return action_value
            else:
                raise Exception("unknown action")
    return None


__all__ = ["Executor", "Transition", "system", "create_executor", "executor"]
