# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

from rigorous.core import terms, unification
from rigorous.data import numbers


def test_addition() -> None:
    x, y, z = terms.variables("x", "y", "z")
    solver = unification.Solver()
    solver.add_equation((numbers.create(7), numbers.add(x, y)))
    assert not solver.is_solved
    assert not solver.has_no_solutions
    solver.add_equation((x, numbers.create(3)))
    solver.add_equation((y, numbers.create(4)))
    assert solver.is_solved
    assert not solver.has_no_solutions
