# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import typing as t

from ...core import terms
from ...data import sets
from ...utils import parser

from .. import sos

from . import semantics


class TokenType(parser.TokenTypeEnum):
    NULL = r"0"
    DOT = r"\."
    FIX = r"fix"
    RESTRICT = r"\\"
    LEFT_BRACE = r"{"
    RIGHT_BRACE = r"}"
    LEFT_PAR = r"\("
    RIGHT_PAR = r"\)"
    COMMA = r","
    EQUALS = r"="
    PARALLEL = r"\|\|"
    CHOICE = r"\+"

    COM_ACTION = r"(?P<action_name>[a-z]+)(?P<action_modifier>\?|!)"
    INT_ACTION = r"τ|tau|i"
    VARIABLE = r"[A-Z]+"

    SPACE = r"\s+", True
    ERROR = r"."


tokenizer = parser.Tokenizer(TokenType)


class CCSSyntaxError(Exception):
    pass


_BINARY_OPERATORS = {
    TokenType.CHOICE: 10,
    TokenType.PARALLEL: 8,
    TokenType.RESTRICT: 6,
}


def _parse_action(stream: parser.TokenStream[TokenType]) -> terms.Term:
    token = stream.token
    if stream.accept(TokenType.INT_ACTION):
        return sos.ACTION_TAU
    elif token is not None and stream.accept(TokenType.COM_ACTION):
        name = terms.symbol(token.match.group("action_name"))
        if token.match.group("action_modifier") == "!":
            action = semantics.generative_action(name)
        else:
            action = semantics.reactive_action(name)
        return action
    else:
        raise CCSSyntaxError(f"expected action but found {token or 'EOF'}")


def _parse_atom(stream: parser.TokenStream[TokenType]) -> terms.Term:
    token = stream.token
    if token is None:
        raise CCSSyntaxError("expected process term but found EOF")
    if stream.accept(TokenType.NULL):
        return semantics.DEAD_PROCESS
    elif stream.accept(TokenType.LEFT_PAR):
        process = _parse_binary(stream)
        stream.expect(TokenType.RIGHT_PAR)
        return process
    elif stream.accept(TokenType.VARIABLE):
        return semantics.ProcessVariable(token.text)
    elif stream.accept(TokenType.FIX):
        variable = semantics.ProcessVariable(stream.expect(TokenType.VARIABLE).text)
        stream.expect(TokenType.EQUALS)
        return semantics.fix(variable, _parse_binary(stream))
    action = _parse_action(stream)
    stream.expect(TokenType.DOT)
    return semantics.prefix(action, _parse_atom(stream))


def _parse_binary(
    stream: parser.TokenStream[TokenType], min_precedence: int = -1
) -> terms.Term:
    left = _parse_atom(stream)
    while stream.token and stream.token.typ in _BINARY_OPERATORS:
        if _BINARY_OPERATORS[stream.token.typ] < min_precedence:
            return left
        operator = stream.consume()
        if operator.typ is TokenType.RESTRICT:
            stream.expect(TokenType.LEFT_BRACE)
            action_set: t.Set[terms.Term] = set()
            while not stream.accept(TokenType.RIGHT_BRACE):
                action_set.add(_parse_action(stream))
                if stream.accept(TokenType.COMMA):
                    continue
                else:
                    stream.expect(TokenType.RIGHT_BRACE)
                    break
            left = semantics.restrict(left, sets.create(action_set))
        else:
            right = _parse_binary(stream, _BINARY_OPERATORS[operator.typ] + 1)
            if operator.typ is TokenType.CHOICE:
                left = semantics.choice(left, right)
            else:
                left = semantics.parallel(left, right)
    return left


def parse_ccs(process: str) -> terms.Term:
    stream = tokenizer.create_stream(process)
    term = _parse_binary(stream)
    if stream.token is not None:
        raise CCSSyntaxError(f"expected EOF but found {stream.token}")
    return term
