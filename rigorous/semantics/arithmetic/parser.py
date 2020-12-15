# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

from ...core import terms
from ...data import numbers
from ...utils import parser

from . import semantics


class TokenType(parser.TokenTypeEnum):
    LEFT_PAR = r"\("
    RIGHT_PAR = r"\)"

    ADD = r"\+"
    SUB = r"-"
    MUL = r"\*"
    DIV = r"/"

    INTEGER = r"[0-9]+"

    SPACE = r"\s+", True
    ERROR = r"."


tokenizer = parser.Tokenizer(TokenType)

_PRECEDENCE = {
    TokenType.MUL: 20,
    TokenType.DIV: 20,
    TokenType.ADD: 10,
    TokenType.SUB: 10,
}

_OPERATORS = {
    TokenType.ADD: semantics.BINARY_ADD,
    TokenType.SUB: semantics.BINARY_SUB,
    TokenType.MUL: semantics.BINARY_MUL,
    TokenType.DIV: semantics.BINARY_DIV,
}


class ExpressionSyntaxError(Exception):
    pass


def _parse_atom(stream: parser.TokenStream[TokenType]) -> terms.Term:
    token = stream.token
    if token is None:
        raise ExpressionSyntaxError("expected arithmetic expression but found EOF")
    if stream.accept(TokenType.LEFT_PAR):
        process = _parse_binary(stream)
        stream.expect(TokenType.RIGHT_PAR)
        return process
    elif stream.accept(TokenType.INTEGER):
        return numbers.create(int(token.text))
    raise ExpressionSyntaxError(f"expected arithmetic expression but found {token}")


def _parse_binary(
    stream: parser.TokenStream[TokenType], min_precedence: int = -1
) -> terms.Term:
    left = _parse_atom(stream)
    while stream.token and stream.token.typ in _PRECEDENCE:
        if _PRECEDENCE[stream.token.typ] < min_precedence:
            return left
        operator = stream.consume()
        right = _parse_binary(stream, _PRECEDENCE[operator.typ] + 1)
        left = semantics.binary_expr(left, _OPERATORS[operator.typ], right)
    return left


def parse_expression(code: str) -> terms.Term:
    return _parse_binary(tokenizer.create_stream(code))
