# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import dataclasses as d
import typing as t

import enum

from . import operators

if t.TYPE_CHECKING:
    from . import blocks


@d.dataclass(frozen=True)
class Location:
    row: int
    column: int

    source: t.Optional[str] = None


class Context(enum.Enum):
    STORE = "store"
    LOAD = "load"
    DELETE = "delete"


class AST:
    pass


class Expression(AST):
    pass


@d.dataclass(frozen=True)
class Name(Expression):
    identifier: str
    context: Context


class Literal(Expression):
    pass


class Constant(Literal):
    pass


@d.dataclass(frozen=True)
class String(Constant):
    value: str


@d.dataclass(frozen=True)
class Integer(Constant):
    value: int


@d.dataclass(frozen=True)
class Float(Constant):
    value: float


@d.dataclass(frozen=True)
class Symbol(Constant):
    class Kind(enum.Enum):
        TRUE = "True"
        FALSE = "False"
        NONE = "None"
        ELLIPSIS = "..."

    kind: Kind

    @classmethod
    def create_true(cls) -> Symbol:
        return cls(Symbol.Kind.TRUE)

    @classmethod
    def create_false(cls) -> Symbol:
        return cls(Symbol.Kind.FALSE)

    @classmethod
    def create_none(cls) -> Symbol:
        return cls(Symbol.Kind.NONE)

    @classmethod
    def create_ellipsis(cls) -> Symbol:
        return cls(Symbol.Kind.ELLIPSIS)


@d.dataclass(frozen=True)
class List(Literal):
    elements: t.Tuple[Expression, ...]


@d.dataclass(frozen=True)
class Tuple(Literal):
    elements: t.Tuple[Expression, ...]


@d.dataclass(frozen=True)
class Dict(Literal):
    keys: t.Tuple[Expression, ...]
    values: t.Tuple[Expression, ...]

    @property
    def items(self) -> t.Iterable[t.Tuple[Expression, Expression]]:
        return zip(self.keys, self.values)


@d.dataclass(frozen=True)
class Unary(Expression):
    operator: operators.UnaryOperator
    operand: Expression


@d.dataclass(frozen=True)
class Not(Expression):
    operand: Expression


@d.dataclass(frozen=True)
class Binary(Expression):
    operator: operators.BinaryOperator
    left: Expression
    right: Expression


@d.dataclass(frozen=True)
class Boolean(Expression):
    operator: operators.BooleanOperator
    left: Expression
    right: Expression


@d.dataclass(frozen=True)
class Conditional(Expression):
    condition: Expression
    consequent: Expression
    alternate: Expression


@d.dataclass(frozen=True)
class Comparator(AST):
    operator: operators.ComparisonOperator
    value: Expression


@d.dataclass(frozen=True)
class Comparison(Expression):
    left: Expression
    comparators: t.Tuple[Comparator, ...]


class ArgumentKind(enum.Enum):
    POSITIONAL = "POSITIONAL"
    KEYWORD = "KEYWORD"
    UNPACK_POSITIONAL = "UNPACK_POSITIONAL"
    UNPACK_KEYWORDS = "UNPACK_KEYWORDS"


@d.dataclass(frozen=True)
class Argument:
    value: Expression
    kind: ArgumentKind = ArgumentKind.POSITIONAL
    name: t.Optional[str] = None

    def __post_init__(self) -> None:
        assert (self.name is not None) is (self.kind is ArgumentKind.KEYWORD)


@d.dataclass(frozen=True)
class Call(Expression):
    function: Expression
    arguments: t.Tuple[Argument, ...]


@d.dataclass(frozen=True)
class Yield(Expression):
    value: Expression


@d.dataclass(frozen=True)
class Attribute(Expression):
    value: Expression
    name: str


@d.dataclass(frozen=True)
class Item(Expression):
    value: Expression
    key: Expression


@d.dataclass(frozen=True)
class Lambda(Expression):
    definition: blocks.FunctionDefinition


Target = t.Union[Name, Attribute, Item]


class Statement(AST):
    pass


Body = t.Tuple[Statement, ...]


@d.dataclass(frozen=True)
class Evaluate(Statement):
    expression: Expression


@d.dataclass(frozen=True)
class Assign(Statement):
    target: Target
    value: Expression


@d.dataclass(frozen=True)
class Delete(Statement):
    target: Target


@d.dataclass(frozen=True)
class Raise(Statement):
    exception: t.Optional[Expression]


@d.dataclass(frozen=True)
class Assert(Statement):
    condition: Expression
    message: t.Optional[Expression]


@d.dataclass(frozen=True)
class Pass(Statement):
    pass


@d.dataclass(frozen=True)
class If(Statement):
    condition: Expression
    consequence: Body
    alternate: Body


@d.dataclass(frozen=True)
class For(Statement):
    target: Name
    iterator: Expression
    body: Body
    alternate: Body


@d.dataclass(frozen=True)
class While(Statement):
    condition: Expression
    body: Body
    alternate: Body


@d.dataclass(frozen=True)
class LoopControl(Statement):
    class Kind(enum.Enum):
        CONTINUE = "continue"
        BREAK = "break"

    kind: Kind

    @classmethod
    def create_continue(cls) -> LoopControl:
        return cls(LoopControl.Kind.CONTINUE)

    @classmethod
    def create_break(cls) -> LoopControl:
        return cls(LoopControl.Kind.BREAK)


@d.dataclass(frozen=True)
class ExceptHandler:
    body: Body
    pattern: t.Optional[Expression]
    target: t.Optional[Name]


@d.dataclass(frozen=True)
class Try(Statement):
    body: Body
    handlers: t.Tuple[ExceptHandler, ...]
    final: Body
    alternate: Body


@d.dataclass(frozen=True)
class Return(Statement):
    value: Expression


@d.dataclass(frozen=True)
class ScopeModifier(Statement):
    class Kind(enum.Enum):
        GLOBAL = "global"
        NON_LOCAL = "non-local"

    kind: Kind
    identifiers: t.Tuple[str, ...]
