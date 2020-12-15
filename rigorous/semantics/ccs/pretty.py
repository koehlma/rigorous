# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

from ...core import terms
from ...pretty import console, render

from .. import sos

from . import semantics


@render.register_function_operator(semantics.complement)
def _render_complement(arguments: terms.Arguments, builder: render.BoxBuilder) -> None:
    builder.append_chunk("comp(", math="\\overline{")
    builder.append_term(arguments[0])
    builder.append_chunk(")", math="}")


@render.render_value.register
def _render_process_variable(
    value: semantics.ProcessVariable, builder: render.BoxBuilder
) -> None:
    builder.append_chunk(value.identifier)


renderer = sos.create_renderer(without_environment=False)
renderer.add_math_symbol("∥", math="\\parallel")


def format_process(process: terms.Term) -> str:
    return console.format_term(process, renderer)
