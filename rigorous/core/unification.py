# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>
#
# fmt: off

from __future__ import annotations

import dataclasses as d
import typing as t

import collections

from . import terms


Equation = t.Tuple[terms.Term, terms.Term]


class NoSolutionError(Exception):
    pass


def _substitute(
    term: terms.Term, substitution: terms.Substitution
) -> terms.Term:
    for variable in term.variables:
        if variable in substitution:
            return term.substitute(substitution)
    return term


@d.dataclass(eq=False)
class Solver:
    _failure: bool = False
    _deferred: t.Set[Equation] = d.field(default_factory=set)
    _pending: t.Deque[Equation] = d.field(default_factory=collections.deque)
    _solutions: t.Dict[terms.Variable, terms.Term] = d.field(
        default_factory=dict
    )

    def _reintegrate_deferred(self) -> None:
        self._pending.extend(self._deferred)
        self._deferred.clear()

    def add_equation(self, equation: Equation) -> None:
        self._pending.append(equation)
        self._reintegrate_deferred()

    def add_equations(self, equations: t.Iterable[Equation]) -> None:
        self._pending.extend(equations)
        self._reintegrate_deferred()

    @property
    def has_no_solutions(self) -> bool:
        self.solve()
        return self._failure

    @property
    def is_solved(self) -> bool:
        self.solve()
        return not self._deferred and not self._failure

    @property
    def not_agnostically_solvable(self) -> bool:
        self.solve()
        return bool(self._deferred and not self._failure)

    @property
    def solution(self) -> t.Mapping[terms.Variable, terms.Term]:
        self.solve()
        return self._solutions

    def merge(self, other: Solver) -> None:
        assert not other._failure
        assert self._solutions.keys().isdisjoint(other._solutions.keys())
        self._solutions = {
            variable: solution.substitute(other._solutions)
            for variable, solution in self._solutions.items()
        }
        for variable, solution in other._solutions.items():
            self._solutions[variable] = solution.substitute(self._solutions)
        self._pending.extend(other._pending)
        self._pending.extend(other._deferred)
        self._reintegrate_deferred()

    def solve(self) -> None:
        did_discover_solutions: bool = False
        while self._pending and not self._failure:
            equation = self._pending.popleft()
            left = _substitute(equation[0], self._solutions).evaluated
            right = _substitute(equation[1], self._solutions).evaluated
            if left is None or right is None:
                self._failure = True
                return
            if isinstance(right, terms.Variable):
                if not isinstance(left, terms.Variable):
                    left, right = right, left
            if isinstance(left, terms.Variable):
                if left in right.unguarded_variables:
                    self._failure = True
                    return
                self._solutions, solutions = {}, self._solutions
                for variable, solution in solutions.items():
                    new_solution = _substitute(
                        solution, {left: right}
                    ).evaluated
                    if new_solution is None:
                        self._failure = True
                        return
                    self._solutions[variable] = new_solution
                self._solutions[left] = right
                did_discover_solutions = True
            elif isinstance(left, terms.Sequence):
                if isinstance(right, terms.Sequence):
                    if left.length != right.length:
                        self._failure = True
                        return
                    self._pending.extend(zip(left.elements, right.elements))
                elif not isinstance(right, terms.Apply):
                    self._failure = True
                    return
                else:
                    self._deferred.add((left, right))
            elif left == right:
                if left.guarded_variables:
                    self._deferred.add((left, right))
            else:
                if not left.is_operator and not right.is_operator:
                    self._failure = True
                    return
                self._deferred.add((left, right))
            if (
                not self._pending
                and not self._failure
                and self._deferred
                and did_discover_solutions
            ):
                did_discover_solutions = False
                self._reintegrate_deferred()

    def clone(self) -> Solver:
        return Solver(
            _failure=self._failure,
            _deferred=set(self._deferred),
            _pending=collections.deque(self._pending),
            _solutions=self._solutions,
        )


def get_solution(
    solutions: terms.Substitution, variable: terms.Variable
) -> terms.Term:
    try:
        return solutions[variable]
    except KeyError:
        for key, value in solutions.items():
            if value == variable:
                return key
        raise NoSolutionError(f"no solution for variable {variable}")


def match(
    pattern: terms.Term, term: terms.Term
) -> t.Optional[terms.Substitution]:
    solver = Solver()
    solver.add_equation((pattern, term))
    if not solver.is_solved or solver.solution.keys() != pattern.variables:
        return None
    return solver.solution
