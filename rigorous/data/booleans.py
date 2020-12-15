# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import dataclasses as d
import typing as t

import warnings

from ..core import inference, terms


@d.dataclass(frozen=True)
class Boolean(terms.Value):
    value: bool


TRUE = Boolean(True)
FALSE = Boolean(False)

_MAP = {True: TRUE, False: FALSE}


def create(value: bool) -> Boolean:
    return _MAP[value]


@terms.function_operator
def land(left: Boolean, right: Boolean) -> t.Optional[terms.Term]:
    return _MAP[left.value and right.value]


@terms.function_operator
def lor(left: Boolean, right: Boolean) -> terms.Term:
    return _MAP[left.value or right.value]


@terms.function_operator
def lnot(operand: Boolean) -> terms.Term:
    return _MAP[not operand.value]


@terms.function_operator
def equals(left: terms.Term, right: terms.Term) -> terms.Term:
    return TRUE if left == right else FALSE


@terms.function_operator
def not_equals(left: terms.Term, right: terms.Term) -> terms.Term:
    return TRUE if left != right else FALSE


@terms.function_operator
def ite(
    condition: Boolean, consequence: terms.Term, alternative: terms.Term
) -> terms.Term:
    return consequence if condition.value else alternative


@d.dataclass(frozen=True)
class BooleanCondition(inference.Condition):
    term: terms.Term

    def get_verdict(self, substitution: terms.Substitution) -> inference.Verdict:
        result = self.term.substitute(substitution).evaluated
        if result is None:
            return inference.Verdict.VIOLATED
        elif isinstance(result, Boolean):
            if result.value:
                return inference.Verdict.SATISFIED
            else:
                return inference.Verdict.VIOLATED
        elif result.is_value:
            # This should not happen and hints at a problem with the inference
            # rules themselves. Let's just emit a warning.
            warnings.warn("term of boolean condition evaluated to non-boolean value")
            return inference.Verdict.VIOLATED
        else:
            return inference.Verdict.SATISFIABLE


def check(term: terms.Term) -> BooleanCondition:
    return BooleanCondition(term)


@terms.function_operator
def is_primitive(term: terms.Term) -> Boolean:
    return _MAP[isinstance(term, terms.Value)]
