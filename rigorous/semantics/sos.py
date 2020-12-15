# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import dataclasses as d
import typing as t

import collections

from ..core import inference, terms
from ..data import booleans
from ..pretty import define, latex, render


def transition(
    source: terms.Term,
    action: terms.Term,
    target: terms.Term,
    *,
    environment: t.Optional[terms.Term] = None,
) -> terms.Term:
    if environment is None:
        return terms.sequence(source, "=", action, "=>", target)
    else:
        return terms.sequence(environment, "⊨", source, "=", action, "=>", target)


some_source = define.variable("some_source", text="s", math="s")
some_target = define.variable("some_target", text="t", math="t")

other_source = define.variable("other_source", text="s'", math="s'")
other_target = define.variable("other_target", text="t'", math="t'")


some_action = define.variable("some_action", text="α", math="\\alpha")
other_action = define.variable("other_action", text="β", math="\\beta")


ACTION_TAU = terms.symbol("τ")


@d.dataclass(frozen=True)
class TransitionElement(render.Special):
    source: render.Box
    action: render.Box
    target: render.Box

    environment: t.Optional[render.Box] = None


_match_source = terms.variable("match_source")
_match_action = terms.variable("match_action")
_match_target = terms.variable("match_target")
_match_environment = terms.variable("match_environment")


RENDER_PATTERN_WITH_ENVIRONMENT = render.SpecialPattern(
    transition(
        _match_source, _match_action, _match_target, environment=_match_environment,
    ),
    (_match_source, _match_action, _match_target, _match_environment),
    TransitionElement,
)

RENDER_PATTERN_WITHOUT_ENVIRONMENT = render.SpecialPattern(
    transition(_match_source, _match_action, _match_target),
    (_match_source, _match_action, _match_target),
    TransitionElement,
)


def create_renderer(
    *, with_environment: bool = True, without_environment: bool = True
) -> render.Renderer:
    renderer = render.Renderer()
    if with_environment:
        renderer.add_pattern(RENDER_PATTERN_WITH_ENVIRONMENT)
    if without_environment:
        renderer.add_pattern(RENDER_PATTERN_WITHOUT_ENVIRONMENT)
    renderer.add_math_symbol("τ", "\\tau")
    renderer.add_math_symbol("⊨", "\\vDash")
    return renderer


@latex.latexify_special.register
def _latexify_transition(special: TransitionElement) -> str:
    parts: t.List[str] = []
    if special.environment is not None:
        parts.append(latex.latexify_box(special.environment))
        parts.append("\\mathbin{\\tSym{\\vDash}}")
    parts.append(latex.latexify_box(special.source))
    parts.append("\\mathbin{\\tSym{\\xrightarrow{{\\color{black}")
    parts.append(latex.latexify_box(special.action))
    parts.append("}}}}")
    parts.append(latex.latexify_box(special.target))
    return " ".join(parts)


default_renderer = create_renderer()


@d.dataclass(frozen=True)
class InferedTransition:
    question: terms.Term
    answer: inference.Answer

    source: terms.Term
    action: terms.Term
    target: terms.Term


@d.dataclass(eq=False)
class Explorer:
    system: inference.System
    deterministic: bool = False

    def iter_transitions(
        self,
        initial_state: terms.Term,
        environment: t.Optional[terms.Term] = None,
        check_determinism: bool = True,
        depth_first: bool = False,
    ) -> t.Iterator[InferedTransition]:
        explored: t.Set[terms.Term] = {initial_state}
        pending: t.Deque[terms.Term] = collections.deque([initial_state])
        while pending:
            state = pending.pop()
            question = transition(
                source=state,
                action=some_action,
                target=some_target,
                environment=environment,
            )
            transitions = 0
            for answer in self.system.iter_answers(question, depth_first=depth_first):
                transitions += 1
                action = answer.substitution[some_action]
                target = answer.substitution[some_target]
                yield InferedTransition(
                    question=question,
                    answer=answer,
                    source=state,
                    action=action,
                    target=target,
                )
                if target not in explored:
                    pending.append(target)
                    explored.add(target)
                if self.deterministic:
                    if transitions > 1:
                        raise Exception(
                            "semantics is supposed to be deterministic but it is not"
                        )
                    if not check_determinism:
                        break


def build_is_action_operator(
    name: str, actions: t.Set[t.Union[str, terms.Symbol]]
) -> terms.FunctionOperator:
    real_actions = {
        action if isinstance(action, terms.Symbol) else terms.symbol(action)
        for action in actions
    }

    def _operator(action: terms.Term) -> t.Optional[terms.Term]:
        if isinstance(action, terms.Sequence):
            action = action.elements[0]
        if isinstance(action, terms.Symbol):
            return booleans.create(action in real_actions)
        return booleans.FALSE

    _operator.__name__ = name
    return terms.function_operator(_operator)
