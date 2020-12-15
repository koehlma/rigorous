# -*- coding: utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

from importlib import resources


builtins_source = resources.read_text(__package__, "builtins.py", encoding="utf-8")
runtime_source = resources.read_text(__package__, "runtime.py", encoding="utf-8")


__all__ = ["builtins_source", "runtime_source"]
