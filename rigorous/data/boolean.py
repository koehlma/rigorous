# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import dataclasses as d
import typing as t

from ..core import terms


@d.dataclass(frozen=True)
class Boolean(terms.Value):
    value: bool


TRUE = Boolean(True)
FALSE = Boolean(False)


@terms.operator
@terms.check_arity(2)
def land(arguments: terms.Arguments) -> t.Optional[terms.Term]:
    x, y = arguments
    if isinstance(x, Boolean) and isinstance(y, Boolean):
        return Boolean(x.value and y.value)
    return None
