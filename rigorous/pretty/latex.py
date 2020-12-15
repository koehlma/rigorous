# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import typing as t

import functools
import re

from ..core import inference, terms

from . import render


_LATEX_ESCAPE = {
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
    "\\": r"\textbackslash{}",
    ">>": r">{}>",
    "<<": r"<{}<",
}

_latex_escape_pattern = re.compile(
    "|".join(re.escape(source) for source in _LATEX_ESCAPE)
)


def _escape_replace(match: t.Match[str]) -> str:
    return _LATEX_ESCAPE[match[0]]


def latex_escape(source: str) -> str:
    return _latex_escape_pattern.sub(_escape_replace, source)


def get_term_color(term: terms.Term) -> t.Optional[str]:
    if isinstance(term, terms.Symbol):
        return "term-symbol"
    elif isinstance(term, terms.Variable):
        return "term-variable"
    elif isinstance(term, terms.Value):
        return "term-value"
    return None


def latexify_box(box: render.Box) -> str:
    chunks: t.List[str] = []
    stack: t.List[t.Union[str, render.Element]] = [box]
    while stack:
        top = stack.pop()
        if isinstance(top, str):
            chunks.append(top)
        elif isinstance(top, render.Chunk):
            chunks.append(top.math or f"\\texttt{{{latex_escape(top.text)}}}")
        else:
            assert isinstance(top, render.Box), f"unexpected non-box element {top}"
            if (special := latexify_special(box.special)) is not None:
                chunks.append(special)
            else:
                color = top.term and get_term_color(top.term)
                if color is not None:
                    chunks.append(f"{{\\color{{{color}}}")
                    stack.append("}")
                stack.extend(reversed(top.elements))
    return " ".join(chunks)


@functools.singledispatch
def latexify_special(special: render.Special) -> t.Optional[str]:
    return None


def latexify_term(term: terms.Term, renderer: render.Renderer) -> str:
    return latexify_box(renderer.render_term(term))


def latexify_rule(rule: inference.Rule, renderer: render.Renderer) -> str:
    buffer: t.List[str] = ["\\begin{prooftree}"]
    hypotheses = len(rule.premises) + len(rule.constraints) + len(rule.conditions)
    for premise in rule.premises:
        buffer.append(f"\\hypo{{{latexify_term(premise, renderer)}}}")
    for left, right in rule.constraints:
        buffer.append(
            f"\\hypo{{{latexify_term(left, renderer)} = {latexify_term(right, renderer)}}}"
        )
    for condition in rule.conditions:
        buffer.append(f"\\hypo{{{latexify_box(renderer.render_condition(condition))}}}")
    conclusion = latexify_term(rule.conclusion, renderer)
    if rule.name:
        name = latex_escape(rule.name)
        buffer.append(f"\\infer{hypotheses}[\\textsc{{{name}}}]{{{conclusion}}}")
    else:
        buffer.append(f"\\infer{hypotheses}{{{conclusion}}}")
    buffer.append("\\end{prooftree}")
    return "\n".join(buffer)
