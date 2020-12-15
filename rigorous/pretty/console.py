# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

"""
Module for pretty printing inference rules and trees on the console.
"""

from __future__ import annotations

import dataclasses as d
import typing as t

import abc
import enum
import functools
import itertools

from ..core import inference, terms

from . import render

try:
    import colorama

    colorama.init()
except ImportError:
    colorama = None


class Color(enum.Enum):
    BLACK = "black"
    RED = "red"
    GREEN = "green"
    YELLOW = "yellow"
    BLUE = "blue"
    MAGENTA = "magenta"
    CYAN = "cyan"
    WHITE = "white"

    RESET = "reset"


if colorama is not None:
    _COLOR_MAP = {
        Color.BLACK: colorama.Fore.BLACK,
        Color.RED: colorama.Fore.RED,
        Color.GREEN: colorama.Fore.GREEN,
        Color.YELLOW: colorama.Fore.YELLOW,
        Color.BLUE: colorama.Fore.BLUE,
        Color.CYAN: colorama.Fore.CYAN,
        Color.MAGENTA: colorama.Fore.MAGENTA,
        Color.WHITE: colorama.Fore.WHITE,
        Color.RESET: colorama.Fore.RESET,
    }
else:
    _COLOR_MAP = {color: "" for color in Color}


@d.dataclass(frozen=True, order=True)
class Position:
    row: int = 0
    column: int = 0


@d.dataclass(frozen=True, order=True)
class Chunk:
    position: Position
    text: str
    columns: int


@d.dataclass(eq=False)
class Canvas:
    colorize: bool = True
    chunks: t.Set[Chunk] = d.field(default_factory=set)
    position: Position = Position()
    stack: t.List[Position] = d.field(default_factory=list)

    def render_text(self, text: str, *, columns: t.Optional[int] = None) -> None:
        self.chunks.add(Chunk(self.position, text, columns or len(text)))

    def store_position(self) -> None:
        self.stack.append(self.position)

    def restore_position(self) -> None:
        self.position = self.stack.pop()

    def advance(self, delta_rows: int = 0, delta_columns: int = 0) -> None:
        self.position = Position(
            self.position.row + delta_rows, self.position.column + delta_columns
        )

    @property
    def text(self) -> str:
        row, column = 0, 0
        lines: t.List[t.List[str]] = []
        line: t.List[str] = []
        for chunk in sorted(self.chunks):
            while chunk.position.row > row:
                lines.append(line)
                line = []
                column = 0
                row += 1
            if chunk.position.column > column:
                line.append(" " * (chunk.position.column - column))
            line.append(chunk.text)
            column = chunk.position.column + chunk.columns
        lines.append(line)
        return "\n".join("".join(line) for line in lines)


class Box(abc.ABC):
    @property
    @abc.abstractmethod
    def columns(self) -> int:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def rows(self) -> int:
        raise NotImplementedError()

    @abc.abstractmethod
    def render(self, canvas: Canvas) -> None:
        raise NotImplementedError()


@d.dataclass(frozen=True)
class Phantom(Box):
    columns: int = 0
    rows: int = 0

    def render(self, canvas: Canvas) -> None:
        pass


@d.dataclass(frozen=True)
class Fragment(Box):
    text: str
    color: t.Optional[Color] = None

    @property
    def columns(self) -> int:
        return len(self.text)

    @property
    def rows(self) -> int:
        return 1

    def render(self, canvas: Canvas) -> None:
        if self.color and canvas.colorize:
            canvas.render_text(
                _COLOR_MAP[self.color] + self.text + _COLOR_MAP[Color.RESET],
                columns=len(self.text),
            )
        else:
            canvas.render_text(self.text)


class Alignment(enum.Enum):
    START = "start"
    CENTER = "center"
    END = "end"


class Direction(enum.Enum):
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


@d.dataclass(frozen=True)
class Container(Box, abc.ABC):
    children: t.Sequence[Box]
    direction: Direction = Direction.HORIZONTAL
    alignment: Alignment = Alignment.CENTER
    spacing: int = 0

    @property
    def total_spacing(self) -> int:
        return self.spacing * (len(self.children) - 1)

    @functools.cached_property
    def columns(self) -> int:  # type: ignore
        if not self.children:
            return 0
        if self.direction is Direction.HORIZONTAL:
            return sum(child.columns for child in self.children) + self.total_spacing
        else:
            return max(child.columns for child in self.children)

    @functools.cached_property
    def rows(self) -> int:  # type: ignore
        if not self.children:
            return 0
        if self.direction is Direction.VERTICAL:
            return sum(child.rows for child in self.children) + self.total_spacing
        else:
            return max(child.rows for child in self.children)

    def render(self, canvas: Canvas) -> None:
        canvas.store_position()
        for child in self.children:
            space = (
                self.rows if self.direction is Direction.HORIZONTAL else self.columns
            )
            size = (
                child.rows if self.direction is Direction.HORIZONTAL else child.columns
            )
            delta = 0
            if self.alignment is Alignment.CENTER:
                delta = (space - size) // 2
            elif self.alignment is Alignment.END:
                delta = space - size
            canvas.store_position()
            if self.direction is Direction.HORIZONTAL:
                canvas.advance(delta_rows=delta)
            else:
                canvas.advance(delta_columns=delta)
            child.render(canvas)
            canvas.restore_position()
            if self.direction is Direction.HORIZONTAL:
                canvas.advance(delta_columns=child.columns + self.spacing)
            else:
                canvas.advance(delta_rows=child.rows + self.spacing)
        canvas.restore_position()


def get_term_color(term: terms.Term) -> t.Optional[Color]:
    if isinstance(term, terms.Symbol):
        return Color.CYAN
    elif isinstance(term, terms.Variable):
        return Color.MAGENTA
    elif isinstance(term, terms.Value):
        return Color.GREEN
    return None


def boxify_box(box: render.Box, term: t.Optional[terms.Term] = None) -> Container:
    fragments: t.List[Fragment] = []
    stack: t.List[t.Tuple[render.Element, t.Optional[terms.Term]]] = [(box, term)]
    while stack:
        element, term = stack.pop()
        if isinstance(element, render.Chunk):
            color = None if term is None else get_term_color(term)
            fragments.append(Fragment(element.text, color=color))
            continue
        assert isinstance(element, render.Box), f"unexpected non-box element {element}"
        stack.extend(
            (child, element.term or term) for child in reversed(element.elements)
        )
    return Container(fragments)


def boxify_term(term: terms.Term, renderer: render.Renderer) -> Container:
    return boxify_box(renderer.render_term(term), term)


def boxify_condition(
    condition: inference.Condition,
    renderer: render.Renderer,
    substitution: t.Optional[terms.Substitution] = None,
) -> Container:
    return boxify_box(renderer.render_condition(condition, substitution))


def boxify_tree(
    tree: inference.Tree, renderer: render.Renderer, *, hollow: bool = False
) -> Container:
    premises = Container(
        tuple(
            itertools.chain(
                (
                    boxify_tree(premise, renderer, hollow=hollow)
                    for premise in tree.premises
                ),
                (
                    Container(
                        (
                            Fragment(" ⋯ ") if hollow else boxify_term(left, renderer),
                            Fragment(" = "),
                            Fragment(" ⋯ ") if hollow else boxify_term(right, renderer),
                        )
                    )
                    for left, right in tree.instance.constraints
                ),
                (
                    Fragment(" ⋯ ")
                    if hollow
                    else boxify_condition(
                        condition, renderer, tree.instance.substitution
                    )
                    for condition in tree.instance.rule.conditions
                ),
            )
        ),
        spacing=3,
        alignment=Alignment.END,
    )
    conclusion = (
        Fragment(" ⋯ ") if hollow else boxify_term(tree.instance.conclusion, renderer)
    )
    line = Fragment("—" * (max(premises.columns, conclusion.columns) + 2))
    return Container(
        (
            Container(
                (
                    Fragment(tree.instance.rule.name or "unnamed"),
                    Phantom(rows=conclusion.rows),
                ),
                direction=Direction.VERTICAL,
            ),
            Container((premises, line, conclusion), direction=Direction.VERTICAL),
        ),
        spacing=1,
        alignment=Alignment.END,
    )


def boxify_rule(rule: inference.Rule, renderer: render.Renderer) -> Container:
    premises = Container(
        tuple(
            itertools.chain(
                (boxify_term(premise, renderer) for premise in rule.premises),
                (
                    Container(
                        (
                            boxify_term(left, renderer),
                            Fragment(" = "),
                            boxify_term(right, renderer),
                        )
                    )
                    for left, right in rule.constraints
                ),
                (
                    boxify_condition(condition, renderer)
                    for condition in rule.conditions
                ),
            )
        ),
        spacing=3,
    )
    conclusion = boxify_term(rule.conclusion, renderer)
    line = Fragment("—" * (max(premises.columns, conclusion.columns) + 2))
    return Container(
        (
            Fragment(rule.name or "unnamed"),
            Container((premises, line, conclusion), direction=Direction.VERTICAL),
        ),
        spacing=1,
    )


def format_rule(
    rule: inference.Rule,
    renderer: render.Renderer,
    *,
    colorize: bool = True,
    indent: int = 0,
) -> str:
    canvas = Canvas(colorize=colorize)
    Container((Fragment(" " * indent), boxify_rule(rule, renderer))).render(canvas)
    return canvas.text


def format_tree(
    tree: inference.Tree,
    renderer: render.Renderer,
    *,
    colorize: bool = True,
    indent: int = 0,
    hollow: bool = False,
) -> str:
    canvas = Canvas(colorize=colorize)
    Container(
        (Fragment(" " * indent), boxify_tree(tree, renderer, hollow=hollow))
    ).render(canvas)
    return canvas.text


def format_term(
    term: terms.Term, renderer: render.Renderer, *, colorize: bool = True
) -> str:
    canvas = Canvas(colorize=colorize)
    boxify_term(term, renderer).render(canvas)
    return canvas.text


def format_condition(
    condition: inference.Condition,
    renderer: render.Renderer,
    *,
    colorize: bool = True,
    indent: int = 0,
) -> str:
    canvas = Canvas(colorize=colorize)
    box = boxify_condition(condition, renderer)
    Container((Fragment(" " * indent), box)).render(canvas)
    return canvas.text
