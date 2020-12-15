# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import dataclasses as d

from ..core import terms

from . import booleans


@d.dataclass(frozen=True)
class String(terms.Value):
    value: str


def create(value: str) -> String:
    return String(value)


@terms.function_operator
def startswith(string: String, prefix: String) -> booleans.Boolean:
    return booleans.create(string.value.startswith(prefix.value))
