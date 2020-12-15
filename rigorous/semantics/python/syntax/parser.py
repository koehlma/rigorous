# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import dataclasses as d
import typing as t

import enum
import functools

from typed_ast import ast3

from mxu.maps import IdentityMap

from . import blocks, operators, tree


class UnsupportedSyntaxError(Exception):
    location: tree.Location

    def __init__(self, message: str, location: tree.Location):
        super().__init__(message)
        self.location = location


_CTX_MAP = {
    ast3.Load: tree.Context.LOAD,
    ast3.Store: tree.Context.STORE,
    ast3.Del: tree.Context.DELETE,
}

_NAME_CONSTANT_MAP = {
    True: tree.Symbol.create_true,
    False: tree.Symbol.create_false,
    None: tree.Symbol.create_none,
    ...: tree.Symbol.create_ellipsis,
}

_BOOLEAN_OPERATOR_MAP = {
    ast3.And: operators.BooleanOperator.AND,
    ast3.Or: operators.BooleanOperator.OR,
}

_UNARY_OPERATOR_MAP = {
    ast3.UAdd: operators.UnaryOperator.PLUS,
    ast3.USub: operators.UnaryOperator.MINUS,
    ast3.Invert: operators.UnaryOperator.INVERT,
}

_BINARY_OPERATOR_MAP = {
    ast3.Add: operators.BinaryOperator.ADD,
    ast3.Sub: operators.BinaryOperator.SUB,
    ast3.Mult: operators.BinaryOperator.MUL,
    ast3.Div: operators.BinaryOperator.REAL_DIV,
    ast3.FloorDiv: operators.BinaryOperator.FLOOR_DIV,
    ast3.Mod: operators.BinaryOperator.MOD,
    ast3.Pow: operators.BinaryOperator.POW,
    ast3.LShift: operators.BinaryOperator.LEFT_SHIFT,
    ast3.RShift: operators.BinaryOperator.RIGHT_SHIFT,
    ast3.BitOr: operators.BinaryOperator.BIT_OR,
    ast3.BitXor: operators.BinaryOperator.BIT_XOR,
    ast3.BitAnd: operators.BinaryOperator.BIT_AND,
    ast3.MatMult: operators.BinaryOperator.MAT_MUL,
}

_COMPARISON_OPERATOR_MAP = {
    ast3.Eq: operators.ComparisonOperator.EQUAL,
    ast3.NotEq: operators.ComparisonOperator.NOT_EQUAL,
    ast3.Lt: operators.ComparisonOperator.LESS,
    ast3.LtE: operators.ComparisonOperator.LESS_EQUAL,
    ast3.Gt: operators.ComparisonOperator.GREATER,
    ast3.GtE: operators.ComparisonOperator.GREATER_EQUAL,
    ast3.Is: operators.ComparisonOperator.IS,
    ast3.IsNot: operators.ComparisonOperator.IS_NOT,
    ast3.In: operators.ComparisonOperator.IN,
    ast3.NotIn: operators.ComparisonOperator.NOT_IN,
}


class Mode(enum.Enum):
    USER = "user"
    PRIMITIVE = "primitive"


@d.dataclass(frozen=True, eq=False)
class _Transformer:
    mode: Mode = Mode.USER

    block_stack: t.List[blocks.Block] = d.field(default_factory=list)

    locations: IdentityMap[tree.AST, tree.Location] = d.field(
        default_factory=IdentityMap
    )

    location_stack: t.List[tree.Location] = d.field(default_factory=list)

    @property
    def top_block(self) -> blocks.Block:
        return self.block_stack[-1]

    def push_block(self, block: blocks.Block) -> None:
        self.block_stack.append(block)

    def pop_block(self) -> None:
        self.block_stack.pop()

    def transform(self, node: t.Union[ast3.stmt, ast3.expr]) -> tree.AST:
        location = tree.Location(node.lineno, node.col_offset)
        try:
            self.location_stack.append(location)
            result = self._transform(node)
        finally:
            self.location_stack.pop()
        assert isinstance(result, (tree.Statement, tree.Expression))
        self.locations[result] = location
        return result

    def transform_expression(self, node: ast3.expr) -> tree.Expression:
        result = self.transform(node)
        assert isinstance(result, tree.Expression)
        return result

    def transform_statement(self, node: ast3.stmt) -> tree.Statement:
        result = self.transform(node)
        assert isinstance(result, tree.Statement)
        return result

    def make_unsupported_error(self, message: str) -> UnsupportedSyntaxError:
        return UnsupportedSyntaxError(message, self.location_stack[-1])

    @functools.singledispatchmethod
    def _transform(self, node: ast3.AST) -> tree.AST:
        raise self.make_unsupported_error(
            f"no transformation implemented for {type(node)}"
        )

    @_transform.register
    def _transform_name(self, node: ast3.Name) -> tree.Expression:
        name = tree.Name(node.id, _CTX_MAP[node.ctx.__class__])
        self.top_block.use(name.identifier, name.context)
        return name

    @_transform.register
    def _transform_str(self, node: ast3.Str) -> tree.Expression:
        return tree.String(node.s)

    @_transform.register
    def _transform_num(self, node: ast3.Num) -> tree.Expression:
        if isinstance(node.n, int):
            return tree.Integer(node.n)
        assert isinstance(node.n, float)
        return tree.Float(node.n)

    @_transform.register
    def _transform_bytes(self, node: ast3.Bytes) -> tree.Expression:
        raise self.make_unsupported_error("byte literals are not supported yet")

    @_transform.register
    def _transform_ellipsis(self, node: ast3.Ellipsis) -> tree.Expression:
        return tree.Symbol.create_ellipsis()

    @_transform.register
    def _transform_name_constant(self, node: ast3.NameConstant) -> tree.Expression:
        return _NAME_CONSTANT_MAP[node.value]()

    @_transform.register
    def _transform_list(self, node: ast3.List) -> tree.Expression:
        elements = tuple(self.transform_expression(element) for element in node.elts)
        if _CTX_MAP[node.ctx.__class__] is not tree.Context.LOAD:
            raise self.make_unsupported_error("list targets are not supported yet")
        return tree.List(elements)

    @_transform.register
    def _transform_tuple(self, node: ast3.Tuple) -> tree.Expression:
        elements = tuple(self.transform_expression(element) for element in node.elts)
        if _CTX_MAP[node.ctx.__class__] is not tree.Context.LOAD:
            raise self.make_unsupported_error("tuple targets are not supported yet")
        return tree.Tuple(elements)

    @_transform.register
    def _transform_dict(self, node: ast3.Dict) -> tree.Expression:
        if any(key is None for key in node.keys):
            raise self.make_unsupported_error(
                "dictionary expansions are not supported yet"
            )
        keys = tuple(self.transform_expression(key) for key in node.keys)
        values = tuple(self.transform_expression(value) for value in node.values)
        return tree.Dict(keys, values)

    @_transform.register
    def _transform_unary(self, node: ast3.UnaryOp) -> tree.Expression:
        if node.op.__class__ in _UNARY_OPERATOR_MAP:
            operator = _UNARY_OPERATOR_MAP[node.op.__class__]
            operand = self.transform_expression(node.operand)
            if (
                isinstance(operand, tree.Integer)
                and operator is operators.UnaryOperator.MINUS
            ):
                return tree.Integer(-operand.value)
            return tree.Unary(operator, operand)
        else:
            assert node.op.__class__ == ast3.Not
            return tree.Not(self.transform_expression(node.operand))

    @_transform.register
    def _transform_binary(self, node: ast3.BinOp) -> tree.Expression:
        operator = _BINARY_OPERATOR_MAP[node.op.__class__]
        left = self.transform_expression(node.left)
        right = self.transform_expression(node.right)
        return tree.Binary(operator, left, right)

    @_transform.register
    def _transform_boolean(self, node: ast3.BoolOp) -> tree.Expression:
        operator = _BOOLEAN_OPERATOR_MAP[node.op.__class__]
        right = self.transform_expression(node.values[-1])
        for left in reversed(node.values[:-1]):
            right = tree.Boolean(operator, self.transform_expression(left), right)
        return right

    @_transform.register
    def _transform_conditional(self, node: ast3.IfExp) -> tree.Expression:
        return tree.Conditional(
            self.transform_expression(node.test),
            self.transform_expression(node.body),
            self.transform_expression(node.orelse),
        )

    @_transform.register
    def _transform_comparison(self, node: ast3.Compare) -> tree.Expression:
        left = self.transform_expression(node.left)
        comparators: t.List[tree.Comparator] = []
        for operator, value in zip(node.ops, node.comparators):
            comparators.append(
                tree.Comparator(
                    _COMPARISON_OPERATOR_MAP[operator.__class__],
                    self.transform_expression(value),
                )
            )
        return tree.Comparison(left, tuple(comparators))

    @_transform.register
    def _transform_call(self, node: ast3.Call) -> tree.Expression:
        function = self.transform_expression(node.func)
        arguments: t.List[tree.Argument] = []
        for positional_argument in node.args:
            if isinstance(positional_argument, ast3.Starred):
                arguments.append(
                    tree.Argument(
                        self.transform_expression(positional_argument.value),
                        kind=tree.ArgumentKind.UNPACK_POSITIONAL,
                    )
                )
            else:
                arguments.append(
                    tree.Argument(self.transform_expression(positional_argument))
                )
        for keyword_argument in node.keywords:
            if keyword_argument.arg:
                arguments.append(
                    tree.Argument(
                        self.transform_expression(keyword_argument.value),
                        kind=tree.ArgumentKind.KEYWORD,
                        name=keyword_argument.arg,
                    )
                )
            else:
                arguments.append(
                    tree.Argument(
                        self.transform_expression(keyword_argument.value),
                        kind=tree.ArgumentKind.UNPACK_KEYWORDS,
                    )
                )
        return tree.Call(function, tuple(arguments))

    @_transform.register
    def _transform_yield(self, node: ast3.Yield) -> tree.Expression:
        self.top_block.contains_yield = True
        value: tree.Expression = tree.Symbol.create_none()
        if node.value is not None:
            value = self.transform_expression(node.value)
        return tree.Yield(value)

    @_transform.register
    def _transform_attribute(self, node: ast3.Attribute) -> tree.Expression:
        value = self.transform_expression(node.value)
        return tree.Attribute(value, node.attr)

    @_transform.register
    def _transform_index(self, node: ast3.Subscript) -> tree.Expression:
        value = self.transform_expression(node.value)
        if not isinstance(node.slice, ast3.Index):
            raise self.make_unsupported_error(
                "only single index subscript expressions are currently supported"
            )
        key = self.transform_expression(node.slice.value)
        return tree.Item(value, key)

    @_transform.register
    def _transform_lambda(self, node: ast3.Lambda) -> tree.Expression:
        parameters = self._transform_arguments(node.args)
        definition = self.top_block.define_function("<lambda>", (), parameters)
        self.push_block(definition)
        definition.body.append(tree.Return(self.transform_expression(node.body)))
        self.pop_block()
        return tree.Lambda(definition)

    @_transform.register
    def _transform_expression_statement(self, node: ast3.Expr) -> tree.Statement:
        return tree.Evaluate(self.transform_expression(node.value))

    @_transform.register
    def _transform_assign(self, node: ast3.Assign) -> tree.Statement:
        if len(node.targets) != 1:
            raise self.make_unsupported_error(
                "only a single assignment target is currently supported"
            )
        target = self.transform_expression(node.targets[0])
        if not isinstance(target, (tree.Name, tree.Attribute, tree.Item)):
            raise self.make_unsupported_error(f"unsupported assignment target {target}")
        value = self.transform_expression(node.value)
        return tree.Assign(target, value)

    @_transform.register
    def _transform_delete(self, node: ast3.Delete) -> tree.Statement:
        if len(node.targets) != 1:
            raise self.make_unsupported_error(
                "only a single deletion target is currently supported"
            )
        target = self.transform_expression(node.targets[0])
        if not isinstance(target, (tree.Name, tree.Attribute, tree.Item)):
            raise self.make_unsupported_error(f"unsupported deletion target {target}")
        return tree.Delete(target)

    @_transform.register
    def _transform_raise(self, node: ast3.Raise) -> tree.Statement:
        exception: t.Optional[tree.Expression] = None
        if node.exc is not None:
            exception = self.transform_expression(node.exc)
        if node.cause is not None:
            raise self.make_unsupported_error(
                "raise statements with a cause are not supported yet"
            )
        return tree.Raise(exception)

    @_transform.register
    def _transform_assert(self, node: ast3.Assert) -> tree.Statement:
        condition = self.transform_expression(node.test)
        message: t.Optional[tree.Expression] = None
        if node.msg is not None:
            message = self.transform_expression(node.msg)
        return tree.Assert(condition, message)

    @_transform.register
    def _transform_pass(self, node: ast3.Pass) -> tree.Statement:
        return tree.Pass()

    @_transform.register
    def _transform_if(self, node: ast3.If) -> tree.Statement:
        condition = self.transform_expression(node.test)
        consequence = tuple(
            self.transform_statement(statement) for statement in node.body
        )
        alternate = tuple(
            self.transform_statement(statement) for statement in node.orelse
        )
        return tree.If(condition, consequence, alternate)

    @_transform.register
    def _transform_for(self, node: ast3.For) -> tree.Statement:
        target = self.transform_expression(node.target)
        if not isinstance(target, tree.Name):
            raise self.make_unsupported_error(
                f"unsupported target {target} in for loop"
            )
        iterator = self.transform_expression(node.iter)
        body = tuple(self.transform_statement(statement) for statement in node.body)
        alternate = tuple(
            self.transform_statement(statement) for statement in node.orelse
        )
        return tree.For(target, iterator, body, alternate)

    @_transform.register
    def _transform_while(self, node: ast3.While) -> tree.Statement:
        condition = self.transform_expression(node.test)
        body = tuple(self.transform_statement(statement) for statement in node.body)
        alternate = tuple(
            self.transform_statement(statement) for statement in node.orelse
        )
        return tree.While(condition, body, alternate)

    @_transform.register
    def _transform_continue(self, node: ast3.Continue) -> tree.Statement:
        return tree.LoopControl.create_continue()

    @_transform.register
    def _transform_break(self, node: ast3.Break) -> tree.Statement:
        return tree.LoopControl.create_break()

    @_transform.register
    def _transform_try(self, node: ast3.Try) -> tree.Statement:
        body = tuple(self.transform_statement(statement) for statement in node.body)
        handlers: t.List[tree.ExceptHandler] = []
        for handler in node.handlers:
            handler_body = tuple(
                self.transform_statement(statement) for statement in handler.body
            )
            handler_match: t.Optional[tree.Expression] = None
            if handler.type:
                handler_match = self.transform_expression(handler.type)
            handler_target: t.Optional[tree.Name] = None
            if handler.name:
                handler_target = tree.Name(handler.name, tree.Context.STORE)
                self.top_block.use(handler_target.identifier, handler_target.context)
            handlers.append(
                tree.ExceptHandler(handler_body, handler_match, handler_target)
            )
        final = tuple(
            self.transform_statement(statement) for statement in node.finalbody
        )
        alternate = tuple(
            self.transform_statement(statement) for statement in node.orelse
        )
        return tree.Try(body, tuple(handlers), final, alternate)

    @_transform.register
    def _transform_return(self, node: ast3.Return) -> tree.Statement:
        value: tree.Expression = tree.Symbol.create_none()
        if node.value:
            value = self.transform_expression(node.value)
        return tree.Return(value)

    @_transform.register
    def _transform_nonlocal(self, node: ast3.Nonlocal) -> tree.Statement:
        identifiers = tuple(node.names)
        for identifier in identifiers:
            self.top_block.declare_nonlocal(identifier)
        return tree.ScopeModifier(tree.ScopeModifier.Kind.NON_LOCAL, identifiers)

    @_transform.register
    def _transform_global(self, node: ast3.Global) -> tree.Statement:
        identifiers = tuple(node.names)
        for identifier in identifiers:
            self.top_block.declare_global(identifier)
        return tree.ScopeModifier(tree.ScopeModifier.Kind.GLOBAL, identifiers)

    def _transform_arguments(
        self, arguments: ast3.arguments
    ) -> t.List[blocks.Parameter]:
        parameters: t.List[blocks.Parameter] = []
        defaults_start = len(arguments.args) - len(arguments.defaults)
        for position, arg in enumerate(arguments.args):
            default: t.Optional[tree.Expression] = None
            if position >= defaults_start:
                default_index = position - defaults_start
                if arguments.defaults[default_index] is not None:
                    default = self.transform_expression(
                        arguments.defaults[default_index]
                    )
            parameters.append(blocks.Parameter(arg.arg, default))
        if arguments.vararg:
            parameters.append(
                blocks.Parameter(
                    arguments.vararg.arg, kind=blocks.ParameterKind.VARIABLE_POSITIONAL,
                )
            )
        for position, arg in enumerate(arguments.kwonlyargs):
            default = None
            if arguments.kw_defaults[position] is not None:
                default = self.transform_expression(arguments.kw_defaults[position])
            parameters.append(
                blocks.Parameter(
                    arg.arg, default, kind=blocks.ParameterKind.KEYWORD_ONLY
                )
            )
        if arguments.kwarg:
            parameters.append(
                blocks.Parameter(
                    arguments.kwarg.arg, kind=blocks.ParameterKind.VARIABLE_KEYWORD,
                )
            )
        return parameters

    @_transform.register
    def _transform_function_definition(self, node: ast3.FunctionDef) -> tree.Statement:
        identifier = node.name
        assert not getattr(
            node.args, "posonlyargs", None
        ), "positional-only arguments are not supported yet"
        parameters = self._transform_arguments(node.args)
        decorators = tuple(
            self.transform_expression(decorator) for decorator in node.decorator_list
        )
        definition = self.top_block.define_function(identifier, decorators, parameters)
        self.push_block(definition)
        definition.body.extend(
            self.transform_statement(statement) for statement in node.body
        )
        self.pop_block()
        return definition

    @_transform.register
    def _transform_class_definition(self, node: ast3.ClassDef) -> tree.Statement:
        identifier = node.name
        decorators = tuple(
            self.transform_expression(decorator) for decorator in node.decorator_list
        )
        arguments: t.List[tree.Argument] = []
        for base in node.bases:
            if isinstance(base, ast3.Starred):
                arguments.append(
                    tree.Argument(
                        self.transform_expression(base.value),
                        kind=tree.ArgumentKind.UNPACK_POSITIONAL,
                    )
                )
            else:
                arguments.append(
                    tree.Argument(
                        self.transform_expression(base),
                        kind=tree.ArgumentKind.POSITIONAL,
                    )
                )
        for keyword_argument in node.keywords:
            if keyword_argument.arg:
                arguments.append(
                    tree.Argument(
                        self.transform_expression(keyword_argument.value),
                        kind=tree.ArgumentKind.KEYWORD,
                        name=keyword_argument.arg,
                    )
                )
            else:
                arguments.append(
                    tree.Argument(
                        self.transform_expression(keyword_argument.value),
                        kind=tree.ArgumentKind.UNPACK_KEYWORDS,
                    )
                )
        definition = self.top_block.define_class(
            identifier, decorators, tuple(arguments)
        )
        self.push_block(definition)
        definition.body.extend(
            self.transform_statement(statement) for statement in node.body
        )
        self.pop_block()
        return definition

    @_transform.register
    def _transform_import_from(self, node: ast3.ImportFrom) -> tree.Statement:
        if self.mode is Mode.USER:
            raise self.make_unsupported_error("import statements are not supported yet")
        return tree.Pass()


def parse_module(code: str, *, mode: Mode = Mode.USER) -> blocks.Module:
    module = blocks.Module()
    transformer = _Transformer(mode=mode, locations=module.locations)
    transformer.push_block(module)
    tree = ast3.parse(code)
    assert isinstance(tree, ast3.Module)
    module.body.extend(
        transformer.transform_statement(statement) for statement in tree.body
    )
    module.infer_mechanisms()
    return module
