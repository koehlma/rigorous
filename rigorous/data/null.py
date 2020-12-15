# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import dataclasses as d

from ..core import terms


@d.dataclass(frozen=True)
class Null(terms.Value):
    pass


NULL = Null()
