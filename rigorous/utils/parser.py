# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import dataclasses as d
import typing as t

import enum
import re


class TokenTypeEnum(enum.Enum):
    regex: str
    ignore: bool

    def __init__(self, regex: str, ignore: bool = False) -> None:
        self.regex = regex
        self.ignore = ignore


TokenType = t.TypeVar("TokenType", bound=TokenTypeEnum)


class Tokenizer(t.Generic[TokenType]):
    token_enum: t.Type[TokenType]

    _tokenize_regex: re.Pattern[str]

    def __init__(self, token_enum: t.Type[TokenType]) -> None:
        self.token_enum = token_enum
        self._tokenize_regex = re.compile(
            "|".join(fr"(?P<{typ.name}>{typ.regex})" for typ in self.token_enum)
        )

    def tokenize(self, code: str) -> t.Iterator[Token[TokenType]]:
        for match in self._tokenize_regex.finditer(code):
            assert isinstance(match.lastgroup, str)
            yield Token(self.token_enum[match.lastgroup], match, match.group(0))

    def create_stream(self, code: str) -> TokenStream[TokenType]:
        return TokenStream(list(self.tokenize(code)))


@d.dataclass(frozen=True)
class Token(t.Generic[TokenType]):
    typ: TokenType
    match: t.Match[str]
    text: str


class UnexpectedTokenError(Exception):
    pass


@d.dataclass(eq=False)
class TokenStream(t.Generic[TokenType]):
    tokens: t.Sequence[Token[TokenType]]
    position: int = 0

    def __post_init__(self) -> None:
        self._skip_ignore()

    def _skip_ignore(self) -> None:
        while self.token and self.token.typ.ignore:
            self.position += 1

    @property
    def token(self) -> t.Optional[Token[TokenType]]:
        try:
            return self.tokens[self.position]
        except IndexError:
            return None

    def consume(self) -> Token[TokenType]:
        token = self.tokens[self.position]
        self.position += 1
        self._skip_ignore()
        return token

    def expect(self, typ: TokenType) -> Token[TokenType]:
        if self.token and self.token.typ is typ:
            return self.consume()
        raise UnexpectedTokenError(
            f"expected token of type {typ} but found {self.token or 'EOF'}"
        )

    def accept(self, typ: TokenType) -> t.Optional[Token[TokenType]]:
        if self.token and self.token.typ is typ:
            return self.consume()
        return None
