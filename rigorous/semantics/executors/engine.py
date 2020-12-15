# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

"""
An executer based on the inference engine.
"""

from __future__ import annotations

import dataclasses as d
import typing as t

import collections

from ...core import inference, terms

from .. import sos

from . import interface


@d.dataclass(frozen=True)
class Transition(interface.Transition):
    question: terms.Term
    answer: inference.Answer

    source: terms.Term
    action: terms.Term
    target: terms.Term

    internal_transitions: int = 1


@d.dataclass(eq=False)
class Executor(interface.Executor[Transition]):
    system: inference.System

    check_determinism: bool = False
    depth_first: bool = False

    def iter_transitions(
        self, initial_state: terms.Term, environment: t.Optional[terms.Term] = None,
    ) -> t.Iterator[Transition]:
        explored: t.Set[terms.Term] = {initial_state}
        pending: t.Deque[terms.Term] = collections.deque([initial_state])
        while pending:
            state = pending.pop()
            question = sos.transition(
                source=state,
                action=sos.some_action,
                target=sos.some_target,
                environment=environment,
            )
            transitions = 0
            for answer in self.system.iter_answers(
                question, depth_first=self.depth_first
            ):
                transitions += 1
                action = answer.substitution[sos.some_action]
                target = answer.substitution[sos.some_target]
                yield Transition(
                    question=question,
                    answer=answer,
                    source=state,
                    action=action,
                    target=target,
                )
                if target not in explored:
                    pending.append(target)
                    explored.add(target)
                if self.check_determinism and transitions > 1:
                    raise Exception(
                        "semantics is supposed to be deterministic but it is not"
                    )
