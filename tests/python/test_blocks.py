# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

from rigorous.semantics.python.syntax import blocks, parser


MECHANISMS_TEST_MODULE = """
def f(y):
    x = 3  # mechanism LOCAL
    y = 2  # mechanism CELL
    z = 1  # mechanism CELL
    
    class B:  # mechanism LOCAL
        y  # mechanism CLASS_CELL
        a  # mechanism CLASS_GLOBAL

        def h():
            y  # mechanism CELL, but not of B but of f

    def g():  # mechanism LOCAL
        global x
        x  # mechanism GLOBAL
        y  # mechanism LOCAL
        y = 2  # mechanism LOCAL
        nonlocal z
        z = 1  # mechanism CELL

    a  # mechanism GLOBAL

x  # mechanism GLOBAL
y  # mechanism GLOBAL
"""


def test_usage_mechanisms() -> None:
    module = parser.parse_module(MECHANISMS_TEST_MODULE)
    assert module.get_mechanism("f") is blocks.Mechanism.GLOBAL
    assert module.get_mechanism("x") is blocks.Mechanism.GLOBAL
    assert module.get_mechanism("y") is blocks.Mechanism.GLOBAL
    assert len(module.children) == 1
    block_f = module.children[0]
    assert block_f.get_mechanism("x") is blocks.Mechanism.LOCAL
    assert block_f.get_mechanism("y") is blocks.Mechanism.CELL
    assert block_f.get_mechanism("z") is blocks.Mechanism.CELL
    assert block_f.get_mechanism("a") is blocks.Mechanism.GLOBAL
    assert block_f.get_mechanism("B") is blocks.Mechanism.LOCAL
    assert block_f.get_mechanism("g") is blocks.Mechanism.LOCAL
    assert len(block_f.children) == 2
    block_f_cls = block_f.children[0]
    assert block_f_cls.get_mechanism("y") is blocks.Mechanism.CLASS_CELL
    assert block_f_cls.get_mechanism("a") is blocks.Mechanism.CLASS_GLOBAL
    assert block_f_cls.get_mechanism("h") is blocks.Mechanism.CLASS_GLOBAL
    assert len(block_f_cls.children) == 1
    block_f_cls_h = block_f_cls.children[0]
    assert block_f_cls_h.get_mechanism("y") is blocks.Mechanism.CELL
    assert block_f_cls_h.get_cell("y").origin is block_f
    block_f_g = block_f.children[1]
    assert block_f_g.get_mechanism("x") is blocks.Mechanism.GLOBAL
    assert block_f_g.get_mechanism("y") is blocks.Mechanism.LOCAL
    assert block_f_g.get_mechanism("z") is blocks.Mechanism.CELL
