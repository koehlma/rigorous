# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>
#
# fmt: off

from __future__ import annotations

import dataclasses as d
import typing as t

import abc
import collections
import enum
import functools
import itertools

from . import terms, unification


class Verdict(enum.Enum):
    SATISFIABLE = "satisfiable"
    VIOLATED = "violated"
    SATISFIED = "satisfied"


class Condition(abc.ABC):
    @abc.abstractmethod
    def get_verdict(self, substititon: terms.Substitution) -> Verdict:
        pass


Premises = t.Tuple[terms.Term, ...]
Constraints = t.Tuple[unification.Equation, ...]
Conditions = t.Tuple[Condition, ...]


@d.dataclass(frozen=True)
class Rule:
    conclusion: terms.Term
    premises: Premises = ()
    constraints: Constraints = ()
    conditions: Conditions = ()
    name: t.Optional[str] = None

    @functools.cached_property
    def variables(self) -> t.AbstractSet[terms.Variable]:
        variables = set(self.conclusion.variables)
        for premise in self.premises:
            variables |= premise.variables
        for left, right in self.constraints:
            variables |= left.variables | right.variables
        return frozenset(variables)


@d.dataclass(frozen=True)
class Instance:
    rule: Rule
    substitution: terms.Substitution

    def __post_init__(self) -> None:
        assert self.rule.variables == self.substitution.keys()

    def _instantiate(
        self, term: terms.Term, *, evaluate: bool = True
    ) -> terms.Term:
        result = term.substitute(self.substitution)
        if evaluate:
            assert result.evaluated is not None
            result = result.evaluated
        return result

    @functools.cached_property
    def conclusion(self) -> terms.Term:
        return self._instantiate(self.rule.conclusion)

    @functools.cached_property
    def premises(self) -> t.Sequence[terms.Term]:
        return tuple(
            self._instantiate(premise) for premise in self.rule.premises
        )

    @functools.cached_property
    def constraints(self) -> t.Sequence[unification.Equation]:
        return tuple(
            (self._instantiate(left), self._instantiate(right, evaluate=False))
            for left, right in self.rule.constraints
        )


@d.dataclass(frozen=True)
class Tree:
    instance: Instance
    premises: t.Tuple[Tree, ...]


Question = terms.Term


@d.dataclass(frozen=True)
class Answer:
    substitution: terms.Substitution
    tree: Tree


@d.dataclass(eq=False)
class System:
    _rules: t.List[Rule]

    def __init__(self, rules: t.Optional[t.Iterable[Rule]] = None) -> None:
        self._rules = []
        if rules is not None:
            for rule in rules:
                self.add_rule(rule)

    def add_rule(self, rule: Rule) -> None:
        self._rules.append(rule)

    @property
    def rules(self) -> t.Sequence[Rule]:
        return self._rules

    def iter_answers(
        self, question: Question, *, depth_first: bool = False
    ) -> t.Iterator[Answer]:
        variables = question.variables
        queue = collections.deque([_Node.create_root(self, question)])
        while queue:
            head = queue.popleft()
            if depth_first:
                queue.extendleft(head.expand())
            else:
                queue.extend(head.expand())
            if head.is_solved and variables <= head.solver.solution.keys():
                assert head.solver.is_solved, "not agnostically solvable"
                substitution = head.solver.solution
                yield Answer(
                    {
                        variable: substitution[variable]
                        for variable in variables
                    },
                    head.construct_tree(question),
                )


@d.dataclass(frozen=True, eq=False)
class _RenamedRule:
    original: Rule
    renaming: terms.Renaming
    conclusion: terms.Term
    premises: Premises = ()
    constraints: Constraints = ()


def _create_renamed_rule(rule: Rule) -> _RenamedRule:
    renaming = {variable: variable.clone() for variable in rule.variables}
    return _RenamedRule(
        original=rule,
        renaming=renaming,
        conclusion=rule.conclusion.substitute(renaming),
        premises=tuple(
            premise.substitute(renaming) for premise in rule.premises
        ),
        constraints=tuple(
            (left.substitute(renaming), right.substitute(renaming))
            for left, right in rule.constraints
        ),
    )


@d.dataclass(frozen=True, eq=False)
class _Node:
    system: System

    solver: unification.Solver

    renamed_rules: t.Mapping[terms.Term, _RenamedRule]

    pending_terms: t.Tuple[terms.Term, ...]
    pending_conditions: t.FrozenSet[t.Tuple[_RenamedRule, Condition]]

    @classmethod
    def create_root(cls, system: System, term: terms.Term) -> _Node:
        return cls(system, unification.Solver(), {}, (term,), frozenset())

    @property
    def is_solved(self) -> bool:
        return (
            not self.pending_terms
            and not self.solver.has_no_solutions
            and not self.pending_conditions
        )

    def construct_tree(self, term: terms.Term) -> Tree:
        renamed_rule = self.renamed_rules[term]
        return Tree(
            Instance(
                renamed_rule.original,
                {
                    variable: self.solver.solution.get(
                        renamed_variable, terms.symbol("FATAL_ERROR")
                    )
                    for variable, renamed_variable
                    in renamed_rule.renaming.items()
                },
            ),
            tuple(
                self.construct_tree(premise)
                for premise in renamed_rule.premises
            ),
        )

    def expand(self) -> t.Iterator[_Node]:
        if not self.pending_terms:
            return
        term = self.pending_terms[0]
        for rule in self.system.rules:
            renamed_rule = _create_renamed_rule(rule)
            solver = self.solver.clone()
            solver.add_equation((term, renamed_rule.conclusion))
            if solver.has_no_solutions:
                continue
            solver.add_equations(renamed_rule.constraints)
            if solver.has_no_solutions:
                continue
            pending_conditions: t.Set[t.Tuple[_RenamedRule, Condition]] = set()
            conditions_iterator = itertools.chain(
                self.pending_conditions,
                ((renamed_rule, condition) for condition in rule.conditions),
            )
            for condition_instance, condition in conditions_iterator:
                verdict = condition.get_verdict(
                    {
                        variable: solver.solution[renamed_variable]
                        for variable, renamed_variable
                        in condition_instance.renaming.items()
                        if renamed_variable in solver.solution
                    }
                )
                if verdict is Verdict.VIOLATED:
                    break
                elif verdict is Verdict.SATISFIABLE:
                    pending_conditions.add((condition_instance, condition))
            else:
                yield _Node(
                    self.system,
                    solver,
                    {term: renamed_rule, **self.renamed_rules},
                    renamed_rule.premises + self.pending_terms[1:],
                    frozenset(pending_conditions),
                )
