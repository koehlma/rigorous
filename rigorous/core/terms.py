# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import dataclasses as d
import typing as t

import abc
import collections
import functools


class Term(abc.ABC):
    @property
    @abc.abstractmethod
    def children(self) -> t.Sequence[Term]:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def evaluated(self) -> t.Optional[Term]:
        raise NotImplementedError()

    @abc.abstractmethod
    def substitute(self, substitution: Substitution) -> Term:
        raise NotImplementedError()

    @abc.abstractmethod
    def replace_in_children(self, replacement: Replacement) -> Term:
        raise NotImplementedError()

    def replace(self, replacement: Replacement) -> Term:
        try:
            return replacement[self]
        except KeyError:
            return self.replace_in_children(replacement)

    @functools.cached_property
    def variables(self) -> t.AbstractSet[Variable]:
        if isinstance(self, Variable):
            return frozenset({self})
        variables: t.Set[Variable] = set()
        for child in self.children:
            variables |= child.variables
        return frozenset(variables)

    @functools.cached_property
    def unguarded_variables(self) -> t.AbstractSet[Variable]:
        if isinstance(self, Apply):
            return frozenset()
        elif isinstance(self, Variable):
            return frozenset({self})
        unguarded_variables: t.Set[Variable] = set()
        for child in self.children:
            unguarded_variables |= child.unguarded_variables
        return frozenset(unguarded_variables)

    @functools.cached_property
    def guarded_variables(self) -> t.AbstractSet[Variable]:
        if isinstance(self, Apply):
            return self.variables
        guarded_variables: t.Set[Variable] = set()
        for child in self.children:
            guarded_variables |= child.guarded_variables
        return frozenset(guarded_variables)

    @property
    def can_evaluate(self) -> bool:
        return self.evaluated is not self

    @property
    def is_closed(self) -> bool:
        return not self.variables

    @property
    def is_value(self) -> bool:
        return self.is_closed and not self.can_evaluate

    @property
    def is_variable(self) -> bool:
        return isinstance(self, Variable)

    @property
    def is_operator(self) -> bool:
        return isinstance(self, Apply)

    def iter_subterms(
        self,
        *,
        eliminate_duplicates: bool = False,
        skip_operator_arguments: bool = False,
    ) -> t.Iterator[Term]:
        if eliminate_duplicates:
            pending = {self}
            visited = {self}
            while pending:
                term = pending.pop()
                visited.add(term)
                yield term
                if not skip_operator_arguments or not isinstance(term, Apply):
                    for child in term.children:
                        if child not in visited:
                            pending.add(child)
        else:
            return self.iter_preorder()

    def iter_preorder(
        self, *, skip_operator_arguments: bool = False
    ) -> t.Iterator[Term]:
        queue: t.Deque[Term] = collections.deque([self])
        while queue:
            term = queue.popleft()
            yield term
            if not skip_operator_arguments or not isinstance(term, Apply):
                queue.extendleft(term.children)


class Atom(Term, abc.ABC):
    @property
    def children(self) -> t.Sequence[Term]:
        return ()

    @property
    def evaluated(self) -> Term:
        return self

    def substitute(self, substitution: Substitution) -> Term:
        return self

    def replace_in_children(self, replacement: Replacement) -> Term:
        return self


class Value(Atom, abc.ABC):
    pass


@d.dataclass(frozen=True)
class Symbol(Atom):
    symbol: str


@d.dataclass(frozen=True, eq=False)
class Variable(Atom):
    name: t.Optional[str] = None

    def __repr__(self) -> str:
        return f"<Variable name={self.name!r} @ {id(self):X}>"

    def clone(self, suffix: t.Optional[str] = None) -> Variable:
        name = self.name
        if name is not None and suffix is not None:
            name += suffix
        return Variable(name)

    def substitute(self, substitution: Substitution) -> Term:
        try:
            return substitution[self]
        except KeyError:
            return self


def _substitute_inner(
    parent: Term,
    terms: t.Tuple[Term, ...],
    substitution: Substitution,
    constructor: t.Callable[[t.Tuple[Term, ...]], Term],
) -> Term:
    for variable in parent.variables:
        if variable in substitution:
            break
    else:
        return parent
    is_inner_substituted = False
    substituted_terms: t.List[Term] = []
    for term in terms:
        substituted_term = term.substitute(substitution)
        if substituted_term is not term:
            is_inner_substituted = True
        substituted_terms.append(substituted_term)
    if is_inner_substituted:
        return constructor(tuple(substituted_terms))
    return parent


@d.dataclass(frozen=True)
class Sequence(Term):
    elements: t.Tuple[Term, ...]

    @property
    def children(self) -> t.Sequence[Term]:
        return self.elements

    @functools.cached_property
    def evaluated(self) -> t.Optional[Term]:  # type: ignore
        is_inner_evaluated = False
        evaluated_elements: t.List[Term] = []
        for element in self.elements:
            if element.evaluated is None:
                return None
            if element.evaluated is not element:
                is_inner_evaluated = True
            evaluated_elements.append(element.evaluated)
        if is_inner_evaluated:
            return Sequence(tuple(evaluated_elements))
        return self

    def substitute(self, substitution: Substitution) -> Term:
        return _substitute_inner(self, self.elements, substitution, Sequence)

    def replace_in_children(self, replacement: Replacement) -> Term:
        return Sequence(
            tuple(element.replace(replacement) for element in self.elements)
        )

    @property
    def length(self) -> int:
        return len(self.elements)


class Operator(t.Protocol):
    def apply(self, arguments: t.Tuple[Term, ...]) -> t.Optional[Term]:
        pass


Arguments = t.Tuple[Term, ...]


@d.dataclass(frozen=True)
class Apply(Term):
    operator: Operator
    arguments: Arguments

    @property
    def children(self) -> t.Sequence[Term]:
        return self.arguments

    @functools.cached_property
    def evaluated(self) -> t.Optional[Term]:  # type: ignore
        evaluated_arguments: t.List[Term] = []
        should_compute = True
        is_inner_evaluated = False
        for argument in self.arguments:
            if argument.evaluated is None:
                return None
            if argument.evaluated is not argument:
                is_inner_evaluated = True
            if not argument.evaluated.is_value:
                should_compute = False
            evaluated_arguments.append(argument.evaluated)
        if should_compute:
            return self.operator.apply(tuple(evaluated_arguments))
        elif is_inner_evaluated:
            return Apply(self.operator, tuple(evaluated_arguments))
        else:
            return self

    def substitute(self, substitution: Substitution) -> Term:
        return _substitute_inner(
            self,
            self.arguments,
            substitution,
            lambda arguments: Apply(self.operator, arguments),
        )

    def replace_in_children(self, replacement: Replacement) -> Term:
        return Apply(
            self.operator,
            tuple(argument.replace(replacement) for argument in self.arguments),
        )


Replacement = t.Mapping[Term, Term]
Substitution = t.Mapping[Variable, Term]
Renaming = t.Mapping[Variable, Variable]


def sequence(*elements: t.Union[Term, str]) -> Sequence:
    return Sequence(
        tuple(
            element if isinstance(element, Term) else symbol(element)
            for element in elements
        )
    )


def symbol(symbol: str) -> Symbol:
    return Symbol(symbol)


def variable(name: str) -> Variable:
    return Variable(name)


def variables(*names: str) -> t.Tuple[Variable, ...]:
    return tuple(Variable(name) for name in names)


class Implementation(t.Protocol):
    def __call__(self, arguments: t.Tuple[Term, ...]) -> t.Optional[Term]:
        pass


@d.dataclass(frozen=True, eq=False)
class FunctionOperator(Operator):
    implementation: Implementation

    name: t.Optional[str] = None

    alternatives: t.List[FunctionOperator] = d.field(default_factory=list)

    def apply(self, arguments: t.Tuple[Term, ...]) -> t.Optional[Term]:
        result = self.implementation(arguments)
        if result is None:
            for function_operator in self.alternatives:
                result = function_operator.apply(arguments)
                if result is not None:
                    break
        return result

    def overload(self, function_operator: FunctionOperator) -> FunctionOperator:
        self.alternatives.append(function_operator)
        return function_operator

    def __call__(self, *arguments: Term) -> Term:
        if all(isinstance(argument, Value) for argument in arguments):
            result = self.implementation(arguments)
            assert result is not None, "invalid operation on primitives"
            return result
        return Apply(self, arguments)


def operator(implementation: Implementation) -> FunctionOperator:
    return FunctionOperator(
        implementation, name=getattr(implementation, "__name__", None)
    )


def check_arity(*arities: int) -> t.Callable[[Implementation], Implementation]:
    def decorator(implementation: Implementation) -> Implementation:
        def wrapper(arguments: Arguments) -> t.Optional[Term]:
            if len(arguments) not in arities:
                return None
            return implementation(arguments)

        functools.update_wrapper(wrapper, implementation)
        return wrapper

    return decorator


class InvalidParameterTypeError(Exception):
    pass


def function_operator(function: t.Callable[..., t.Optional[Term]]) -> FunctionOperator:
    import inspect

    signature = inspect.signature(function)
    type_hints = t.get_type_hints(function)

    types: t.Dict[str, t.Type[Term]] = {}
    optionals: t.Set[str] = set()

    for parameter in signature.parameters.values():
        typ = type_hints.get(parameter.name, Term)
        origin = t.get_origin(typ)
        args = t.get_args(typ)
        optional = False
        if origin is t.Union and len(args) == 2 and args[1] is type(None):
            typ = args[0]
            optional = True
        if not isinstance(typ, type) or not issubclass(typ, Term):
            raise InvalidParameterTypeError(
                f"invalid type annotation {typ} for parameter {parameter.name}"
            )
        types[parameter.name] = typ
        if optional:
            optionals.add(parameter.name)

    def implementation(arguments: Arguments) -> t.Optional[Term]:
        try:
            bound_arguments = signature.bind(*arguments)
        except TypeError:
            return None
        else:
            for parameter in signature.parameters.values():
                argument = bound_arguments.arguments.get(parameter.name, None)
                if argument is None:
                    if parameter.name not in optionals:
                        return None
                elif not isinstance(argument, types[parameter.name]):
                    return None
            return function(*arguments)

    return FunctionOperator(implementation, name=getattr(function, "__name__", None))


@function_operator
def replace(base: Term, term: Term, replacement: Term) -> Term:
    return base.replace({term: replacement})
