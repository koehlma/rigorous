# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

from .. import sos


renderer = sos.create_renderer(with_environment=False)
renderer.add_math_symbol("⊥", math="\\bot")
