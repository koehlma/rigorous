# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import pathlib

from ..core import inference

from . import console, define, render


def print_rule(rule: inference.Rule, renderer: render.Renderer) -> None:
    info = define.get_rule_info(rule)
    if info and info.location:
        filename = "/".join(pathlib.Path(info.location.filename).parts[-2:])
        print(f"Rule {rule.name!r} ({filename}:{info.location.lineno}):\n")
    print(console.format_rule(rule, renderer, indent=2))


def print_system(system: inference.System, renderer: render.Renderer) -> None:
    for rule in system.rules:
        print()
        print_rule(rule, renderer)
        print()
