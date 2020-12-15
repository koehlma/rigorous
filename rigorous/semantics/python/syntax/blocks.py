# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import dataclasses as d
import typing as t

import enum

from mxu.maps import IdentityMap

from . import tree


class Mechanism(enum.Enum):
    UNKNOWN = "unknown"  # Will be inferred during annotation phase.

    LOCAL = "local"
    GLOBAL = "global"
    CELL = "cell"

    CLASS_GLOBAL = "class_global"
    CLASS_CELL = "class_cell"


@d.dataclass(eq=False)
class Usage:
    name: str
    mechanism: Mechanism = Mechanism.UNKNOWN
    contexts: t.Set[tree.Context] = d.field(default_factory=set)


@d.dataclass(frozen=True)
class Cell:
    name: str
    origin: Block


class Block(tree.AST):
    module: t.Optional[Module]
    parent: t.Optional[Block]

    children: t.List[Block]

    # The set of names which are bound within the block.
    bound_names: t.Set[str]

    cells: t.Dict[str, Cell]
    usages: t.Dict[str, Usage]

    declared_global: t.Set[str]
    declared_nonlocal: t.Set[str]

    body: t.List[tree.Statement]

    contains_yield: bool

    def __init__(self, *, parent: t.Optional[Block] = None) -> None:
        self.module = None if parent is None else parent.module
        self.parent = parent
        self.children = []
        self.bound_names = set()
        self.cells = {}
        self.usages = {}
        self.declared_global = set()
        self.declared_nonlocal = set()
        self.body = []
        self.contains_yield = False
        self.use("__doc__", tree.Context.STORE)

    def infer_mechanisms(self) -> None:
        for child in self.children:
            child.infer_mechanisms()
        for name, usage in self.usages.items():
            if usage.mechanism is Mechanism.UNKNOWN:
                # In a module all usages should be marked GLOBAL already.
                assert not self.is_module
                if self.is_bound(name) and not self.is_class_definition:
                    usage.mechanism = Mechanism.LOCAL
                else:
                    self.cell(name)

    def is_global(self, name: str) -> bool:
        return name in self.declared_global

    def is_nonlocal(self, name: str) -> bool:
        return name in self.declared_nonlocal

    def is_undeclared(self, name: str) -> bool:
        return name not in self.declared_global and name not in self.declared_nonlocal

    def is_bound(self, name: str) -> bool:
        return name in self.bound_names

    def is_used(self, name: str) -> bool:
        return name in self.usages

    @property
    def is_module(self) -> bool:
        return isinstance(self, Module)

    @property
    def is_class_definition(self) -> bool:
        return isinstance(self, ClassDefinition)

    @property
    def is_function_definition(self) -> bool:
        return isinstance(self, FunctionDefinition)

    def declare_nonlocal(self, name: str) -> None:
        if name == "__class__":
            return
        assert self.is_undeclared(name) and not self.is_used(name)
        self.declared_nonlocal.add(name)

    def declare_global(self, name: str) -> None:
        assert self.is_undeclared(name) and not self.is_used(name)
        self.declared_global.add(name)

    def get_mechanism(self, identifier: str) -> Mechanism:
        return self.usages[identifier].mechanism

    def get_cell(self, identifier: str) -> Cell:
        return self.cells[identifier]

    def define_function(
        self,
        identifier: str,
        decorators: t.Tuple[tree.Expression, ...],
        parameters: t.List[Parameter],
    ) -> FunctionDefinition:
        definition = FunctionDefinition(identifier, decorators, parameters, parent=self)
        self.use(definition.identifier, tree.Context.STORE)
        for parameter in parameters:
            definition.use(parameter.identifier, tree.Context.STORE)
        self.children.append(definition)
        return definition

    def define_class(
        self,
        identifier: str,
        decorators: t.Tuple[tree.Expression, ...],
        arguments: t.Tuple[tree.Argument, ...],
    ) -> ClassDefinition:
        definition = ClassDefinition(identifier, decorators, arguments, parent=self)
        self.use(definition.identifier, tree.Context.STORE)
        self.children.append(definition)
        return definition

    def use(self, identifier: str, context: tree.Context) -> Usage:
        """
        Introduces a new name usage to the block.
        """
        if context is tree.Context.STORE and self.is_undeclared(identifier):
            # A STORE operation binds undeclared names to the block.
            self.bound_names.add(identifier)
        try:
            usage = self.usages[identifier]
        except KeyError:
            if self.is_global(identifier) or self.is_module:
                # Names used in a module or declared global are always accessed via `GLOBAL`.
                mechanism = Mechanism.GLOBAL
            else:
                # The access mechanism will be annotated later when all names are known.
                mechanism = Mechanism.UNKNOWN
            usage = self.usages[identifier] = Usage(identifier, mechanism, {context})
        else:
            usage.contexts.add(context)
        return usage

    def cell(self, name: str) -> t.Optional[Cell]:
        cell: t.Optional[Cell] = None
        if self.is_global(name):
            return None
        try:
            cell = self.cells[name]
        except KeyError:
            if self.parent is None:
                return None
            if self.is_bound(name) and not self.is_class_definition:
                cell = self.cells[name] = Cell(name, self)
                self.usages[name].mechanism = Mechanism.CELL
            else:
                cell = self.parent.cell(name)
                if cell is None:
                    if self.is_undeclared(name) and self.is_class_definition:
                        mechanism = Mechanism.CLASS_GLOBAL
                    else:
                        mechanism = Mechanism.GLOBAL
                else:
                    self.cells[name] = cell
                    if self.is_undeclared(name) and self.is_class_definition:
                        mechanism = Mechanism.CLASS_CELL
                    else:
                        mechanism = Mechanism.CELL
                try:
                    usage = self.usages[name]
                except KeyError:
                    self.usages[name] = Usage(name, mechanism, set())
                else:
                    usage.mechanism = mechanism
        return cell


class Definition(Block, tree.Statement):
    identifier: str
    decorators: t.Tuple[tree.Expression, ...]

    def __init__(
        self,
        identifier: str,
        decorators: t.Tuple[tree.Expression, ...],
        *,
        parent: t.Optional[Block] = None
    ) -> None:
        super().__init__(parent=parent)
        self.identifier = identifier
        self.decorators = decorators


class ParameterKind(enum.Enum):
    POSITIONAL_ONLY = "POSITIONAL_ONLY"
    POSITIONAL_OR_KEYWORD = "POSITIONAL_OR_KEYWORD"
    VARIABLE_POSITIONAL = "VARIABLE_POSITIONAL"
    KEYWORD_ONLY = "KEYWORD_ONLY"
    VARIABLE_KEYWORD = "VARIABLE_KEYWORD"


@d.dataclass(frozen=True)
class Parameter:
    identifier: str
    default: t.Optional[tree.Expression] = None
    kind: ParameterKind = ParameterKind.POSITIONAL_OR_KEYWORD


class FunctionDefinition(Definition):
    parameters: t.List[Parameter]

    def __init__(
        self,
        identifier: str,
        decorators: t.Tuple[tree.Expression, ...],
        parameters: t.List[Parameter],
        *,
        parent: t.Optional[Block] = None
    ) -> None:
        super().__init__(identifier, decorators, parent=parent)
        self.parameters = parameters
        for parameter in self.parameters:
            self.use(parameter.identifier, tree.Context.STORE)


class ClassDefinition(Definition):
    arguments: t.Tuple[tree.Argument, ...]

    def __init__(
        self,
        identifier: str,
        decorators: t.Tuple[tree.Expression, ...],
        arguments: t.Tuple[tree.Argument, ...],
        *,
        parent: t.Optional[Block] = None
    ) -> None:
        super().__init__(identifier, decorators, parent=parent)
        self.arguments = arguments
        self.use("__module__", tree.Context.STORE)

    @property
    def bases(self) -> t.Sequence[tree.Expression]:
        return tuple(
            argument.value
            for argument in self.arguments
            if argument.kind is tree.ArgumentKind.POSITIONAL
        )

    def define_function(
        self,
        identifier: str,
        decorators: t.Tuple[tree.Expression, ...],
        parameters: t.List[Parameter],
    ) -> FunctionDefinition:
        definition = super().define_function(identifier, decorators, parameters)
        definition.usages["__class__"] = Usage(identifier, Mechanism.CELL)
        return definition


class Module(Block):
    locations: IdentityMap[tree.AST, tree.Location]

    def __init__(self) -> None:
        super().__init__()
        self.use("__name__", tree.Context.STORE)
        self.locations = IdentityMap()


@d.dataclass(frozen=True)
class BlockManager:
    block: Block
    stack: Stack

    def __enter__(self) -> None:
        self.stack.push(self.block)

    def __exit__(self, exc_type: t.Any, exc_value: t.Any, exc_tb: t.Any) -> None:
        self.stack.pop()


@d.dataclass(frozen=True, eq=False)
class Stack:
    stack: t.List[Block] = d.field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.stack

    @property
    def head(self) -> Block:
        return self.stack[-1]

    @property
    def predecessor(self) -> t.Optional[Block]:
        try:
            return self.stack[-2]
        except IndexError:
            return None

    def push(self, block: Block) -> None:
        self.stack.append(block)

    def pop(self) -> Block:
        return self.stack.pop()

    def enter(self, block: Block) -> BlockManager:
        return BlockManager(block, self)
