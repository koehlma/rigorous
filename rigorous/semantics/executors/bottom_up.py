# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

"""
An executer constructing inference trees bottom-up.
"""

from __future__ import annotations

import dataclasses as d
import typing as t

import collections
import itertools

from ...core import terms, inference, unification

from .. import sos

from . import interface


_var_source = terms.variable("source")
_var_action = terms.variable("action")
_var_target = terms.variable("target")


_PATTERN = sos.transition(source=_var_source, action=_var_action, target=_var_target)


class NonDeterminismError(Exception):
    state: terms.Term

    def __init__(self, state: terms.Term) -> None:
        super().__init__(state)
        self.state = state


@d.dataclass(frozen=True)
class TransitionTerm:
    source: terms.Term
    action: terms.Term
    target: terms.Term


def decompose_transition(term: terms.Term) -> t.Optional[TransitionTerm]:
    match = unification.match(_PATTERN, term)
    if match:
        return TransitionTerm(
            source=match[_var_source],
            action=match[_var_action],
            target=match[_var_target],
        )
    else:
        return None


@d.dataclass(frozen=True)
class TransitionRule:
    original: inference.Rule
    conclusion: TransitionTerm
    premises: t.Tuple[TransitionTerm, ...]
    variables: t.FrozenSet[terms.Variable]


Renaming = t.Mapping[terms.Variable, terms.Variable]


@d.dataclass(frozen=True)
class _DeferredCondition:
    condition: inference.Condition
    renaming: Renaming
    solution: terms.Substitution

    def get_environment(self, substitution: terms.Substitution) -> terms.Substitution:
        environment = {
            variable: substitution[renamed]
            for variable, renamed in self.renaming.items()
            if renamed in substitution
        }
        environment.update(self.solution)
        return environment

    def get_verdict(self, substitution: terms.Substitution) -> inference.Verdict:
        return self.condition.get_verdict(self.get_environment(substitution))


@d.dataclass(eq=False)
class _Destination:
    action: terms.Term
    target: terms.Term
    solver: unification.Solver
    conditions: t.Sequence[_DeferredCondition]

    internal_transitions: int


@d.dataclass(eq=False)
class _Handle:
    solver: unification.Solver
    premises: t.Sequence[TransitionTerm]
    conditions: t.Sequence[_DeferredCondition]

    internal_transitions: int


@d.dataclass(frozen=True)
class Transition(interface.Transition):
    source: terms.Term
    action: terms.Term
    target: terms.Term

    internal_transitions: int


@d.dataclass(eq=False)
class Executor(interface.Executor[Transition]):
    shortcircuit: bool = True

    transition_rules: t.List[TransitionRule] = d.field(default_factory=list)

    def add_rule(self, rule: inference.Rule) -> None:
        conclusion = decompose_transition(rule.conclusion)
        assert conclusion, "conclusion must be an SOS transition"
        premises: t.List[TransitionTerm] = []
        bound: t.Set[terms.Variable] = set(conclusion.source.variables)
        for premise in rule.premises:
            transition = decompose_transition(premise)
            assert transition, "premises must be SOS transitions"
            # This criterion is necessary but insufficient for the optimizations to
            # work properly. Unfortunately there is no sufficient “local” criterion
            # only considering a single rule. The algorithm will later fail if it
            # finds out that the rules do not satisfy all necessary conditions.
            assert (
                transition.source.variables <= bound
            ), f"transition contains unbound variables {transition.source.variables - bound}"
            bound |= transition.action.variables
            bound |= transition.target.variables
            premises.append(transition)
        self.transition_rules.append(
            TransitionRule(
                original=rule,
                conclusion=conclusion,
                premises=tuple(premises),
                variables=frozenset(rule.variables - conclusion.source.variables),
            )
        )

    def _apply_rule(
        self,
        state: terms.Term,
        rule: TransitionRule,
        cache: t.Dict[terms.Term, t.Sequence[_Destination]],
    ) -> t.Iterable[_Destination]:
        substitution = unification.match(rule.conclusion.source, state)
        if substitution is None:
            return

        renaming = {variable: variable.clone() for variable in rule.variables}

        conditions: t.List[_DeferredCondition] = []
        for condition in rule.original.conditions:
            verdict = condition.get_verdict(substitution)
            if verdict is inference.Verdict.VIOLATED:
                return
            elif verdict is inference.Verdict.SATISFIABLE:
                conditions.append(_DeferredCondition(condition, renaming, substitution))

        substitution = dict(substitution)
        substitution.update(renaming)

        solver = unification.Solver()
        for (left, right) in rule.original.constraints:
            solver.add_equation(
                (left.substitute(substitution), right.substitute(substitution))
            )
        if solver.has_no_solutions:
            return

        action = rule.conclusion.action.substitute(substitution)
        target = rule.conclusion.target.substitute(substitution)

        if not rule.premises:
            yield _Destination(
                action=action,
                target=target,
                solver=solver,
                conditions=conditions,
                internal_transitions=1,
            )
            return

        pending: t.List[_Handle] = [_Handle(solver, rule.premises, conditions, 0)]
        del solver
        del conditions

        while pending:
            handle = pending.pop()
            raw_premise, *remaining = handle.premises
            solution = handle.solver.solution
            premise = TransitionTerm(
                source=raw_premise.source.substitute(substitution).substitute(solution),
                action=raw_premise.action.substitute(substitution).substitute(solution),
                target=raw_premise.target.substitute(substitution).substitute(solution),
            )

            for destination in self._explore(premise.source, cache):
                solver = handle.solver.clone()
                solver.merge(destination.solver)

                if solver.has_no_solutions:
                    continue

                solver.add_equation((premise.action, destination.action))
                solver.add_equation((premise.target, destination.target))

                if solver.has_no_solutions:
                    continue

                solution = solver.solution

                condition_violated: bool = False

                conditions = []
                for deferred_condition in itertools.chain(
                    handle.conditions, destination.conditions
                ):
                    verdict = deferred_condition.get_verdict(solution)
                    if verdict is inference.Verdict.VIOLATED:
                        condition_violated = True
                        break
                    elif verdict is inference.Verdict.SATISFIABLE:
                        conditions.append(deferred_condition)

                if condition_violated:
                    continue

                internal_transitions = max(
                    handle.internal_transitions, destination.internal_transitions,
                )
                if remaining:
                    pending.append(
                        _Handle(solver, remaining, conditions, internal_transitions,)
                    )
                else:
                    yield _Destination(
                        action=action.substitute(solution),
                        target=target.substitute(solution),
                        solver=solver,
                        conditions=conditions,
                        internal_transitions=internal_transitions,
                    )

    def _one_step(
        self, state: terms.Term, cache: t.Dict[terms.Term, t.Sequence[_Destination]],
    ) -> t.Iterable[_Destination]:
        assert not state.variables, "state must not contain any variables"
        try:
            return cache[state]
        except KeyError:
            pass
        destinations = tuple(
            itertools.chain(
                *(
                    self._apply_rule(state, rule, cache)
                    for rule in self.transition_rules
                )
            )
        )
        cache[state] = destinations
        return destinations

    def _explore(
        self, state: terms.Term, cache: t.Dict[terms.Term, t.Sequence[_Destination]],
    ) -> t.Iterable[_Destination]:
        destinations = tuple(self._one_step(state, cache))

        if self.shortcircuit:
            final_destinations: t.List[_Destination] = []
            pending_destinations = collections.deque(destinations)
            while pending_destinations:
                destination = pending_destinations.pop()
                if destination.action != sos.ACTION_TAU or destination.target.variables:
                    final_destinations.append(destination)
                else:
                    has_inner = False
                    for inner_destination in self._one_step(destination.target, cache):
                        pending_destinations.append(
                            _Destination(
                                action=inner_destination.action,
                                target=inner_destination.target,
                                solver=inner_destination.solver,
                                conditions=inner_destination.conditions,
                                internal_transitions=(
                                    inner_destination.internal_transitions
                                    + destination.internal_transitions
                                ),
                            )
                        )
                        has_inner = True
                    if not has_inner:
                        final_destinations.append(destination)
            destinations = tuple(final_destinations)

        cache[state] = destinations
        return destinations

    def iter_transitions(self, initial_state: terms.Term) -> t.Iterator[Transition]:
        pending: t.Deque[terms.Term] = collections.deque([initial_state])
        while pending:
            state = pending.pop()
            counter = 0
            for destination in self._explore(state, {}):
                assert destination.solver.is_solved
                solution = destination.solver.solution
                for deferred_condition in destination.conditions:
                    verdict = deferred_condition.get_verdict(solution)
                    if verdict is not inference.Verdict.SATISFIED:
                        break
                else:
                    counter += 1
                    yield Transition(
                        state,
                        destination.action,
                        destination.target,
                        destination.internal_transitions,
                    )
                    pending.append(destination.target)
            if counter > 1:
                raise NonDeterminismError(state)
