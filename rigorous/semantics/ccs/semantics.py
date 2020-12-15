# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>
#
# fmt: off

from __future__ import annotations

import dataclasses as d
import typing as t

from ...core import terms, inference
from ...data import mappings, sets, booleans
from ...pretty import define
from ...semantics import sos


# Let's introduce process variables and actions as a new data type.
@d.dataclass(frozen=True)
class ProcessVariable(terms.Value):
    identifier: str


# The process that cannot do anything.
DEAD_PROCESS = terms.symbol("0")


@terms.function_operator
def complement(action: terms.Sequence) -> t.Optional[terms.Term]:
    if len(action.elements) != 2:
        return None
    name, modifier = action.elements
    if isinstance(modifier, terms.Symbol):
        if modifier.symbol == "!":
            return terms.sequence(name, "?")
        elif modifier.symbol == "?":
            return terms.sequence(name, "!")
    return None


# Next, we define some auxillary functions to build process terms.


def generative_action(action: terms.Term) -> terms.Term:
    return terms.sequence(action, "!")


def reactive_action(action: terms.Term) -> terms.Term:
    return terms.sequence(action, "?")


def prefix(action: terms.Term, process: terms.Term) -> terms.Term:
    return terms.sequence(action, ".", process)


def choice(left: terms.Term, right: terms.Term) -> terms.Term:
    return terms.sequence(left, "+", right)


def parallel(left: terms.Term, right: terms.Term) -> terms.Term:
    return terms.sequence(left, "∥", right)


def restrict(process: terms.Term, actions: terms.Term) -> terms.Term:
    return terms.sequence(process, terms.symbol("\\"), actions)


def fix(process_variable: terms.Term, process: terms.Term) -> terms.Term:
    return terms.sequence(
        terms.symbol("fix"), process_variable, terms.symbol("="), process
    )


def create_environment(
    binding: t.Mapping[terms.Term, terms.Term]
) -> terms.Term:
    return mappings.create(binding)


# We are going to need some meta variables for our inference rules.

some_environment = define.variable("the_env", text="Γ", math="\\Gamma")

some_process = define.variable("some_process", text="P", math="P")
some_successor = define.variable("some_successor", text="P'", math="P'")

other_process = define.variable("other_process", text="Q", math="Q")
other_successor = define.variable("other_successor", text="Q'", math="Q'")

process_variable = define.variable("process_variable", text="X", math="X")

action_set = define.variable("action_set", text="H", math="H")


prefix_rule = define.rule(
    "prefix",
    conclusion=sos.transition(
        environment=some_environment,
        source=prefix(sos.some_action, some_process),
        action=sos.some_action,
        target=some_process,
    ),
)

choice_l_rule = define.rule(
    "choice-l",
    premises=(
        sos.transition(
            environment=some_environment,
            source=some_process,
            action=sos.some_action,
            target=some_successor,
        ),
    ),
    conclusion=sos.transition(
        environment=some_environment,
        source=choice(some_process, other_process),
        action=sos.some_action,
        target=some_successor,
    ),
)

choice_r_rule = define.rule(
    "choice-r",
    premises=(
        sos.transition(
            environment=some_environment,
            source=other_process,
            action=sos.some_action,
            target=other_successor,
        ),
    ),
    conclusion=sos.transition(
        environment=some_environment,
        source=choice(some_process, other_process),
        action=sos.some_action,
        target=other_successor,
    ),
)

par_l_rule = define.rule(
    "par-l",
    premises=(
        sos.transition(
            environment=some_environment,
            source=some_process,
            action=sos.some_action,
            target=some_successor,
        ),
    ),
    conclusion=sos.transition(
        environment=some_environment,
        source=parallel(some_process, other_process),
        action=sos.some_action,
        target=parallel(some_successor, other_process),
    ),
)

par_r_rule = define.rule(
    "par-r",
    premises=(
        sos.transition(
            environment=some_environment,
            source=other_process,
            action=sos.some_action,
            target=other_successor,
        ),
    ),
    conclusion=sos.transition(
        environment=some_environment,
        source=parallel(some_process, other_process),
        action=sos.some_action,
        target=parallel(some_process, other_successor),
    ),
)

sync_rule = define.rule(
    name="sync",
    premises=(
        sos.transition(
            environment=some_environment,
            source=some_process,
            action=sos.some_action,
            target=some_successor,
        ),
        sos.transition(
            environment=some_environment,
            source=other_process,
            action=complement(sos.some_action),
            target=other_successor,
        ),
    ),
    conclusion=sos.transition(
        environment=some_environment,
        source=parallel(some_process, other_process),
        action=sos.ACTION_TAU,
        target=parallel(some_successor, other_successor),
    ),
)

rec_rule = define.rule(
    "rec",
    premises=(
        sos.transition(
            environment=some_environment,
            source=some_process,
            action=sos.some_action,
            target=some_successor,
        ),
    ),
    constraints=(
        (some_process, mappings.getitem(some_environment, process_variable)),
    ),
    conclusion=sos.transition(
        environment=some_environment,
        source=process_variable,
        action=sos.some_action,
        target=some_successor,
    ),
)

res_rule = define.rule(
    "res",
    premises=(
        sos.transition(
            environment=some_environment,
            source=some_process,
            action=sos.some_action,
            target=some_successor,
        ),
    ),
    conditions=(
        booleans.check(sets.not_contains(action_set, sos.some_action)),
    ),
    conclusion=sos.transition(
        environment=some_environment,
        source=restrict(some_process, action_set),
        action=sos.some_action,
        target=restrict(some_successor, action_set),
    ),
)

fix_rule = define.rule(
    "fix",
    premises=(
        sos.transition(
            environment=some_environment,
            source=terms.replace(
                some_process,
                process_variable,
                fix(process_variable, some_process),
            ),
            action=sos.some_action,
            target=some_successor,
        ),
    ),
    conclusion=sos.transition(
        environment=some_environment,
        source=fix(process_variable, some_process),
        action=sos.some_action,
        target=some_successor,
    ),
)


system = inference.System(
    [
        prefix_rule,
        choice_l_rule,
        choice_r_rule,
        par_l_rule,
        par_r_rule,
        sync_rule,
        rec_rule,
        res_rule,
        fix_rule,
    ]
)
