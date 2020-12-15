# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import typing as t

import pathlib

import click

from ..core import inference
from ..pretty import printers, render, latex


def add_system_commands(
    group: click.Group, system: inference.System, renderer: render.Renderer
) -> None:
    @group.group("system")
    def _system() -> None:
        """
        Inferene rule system specific commands.
        """

    @_system.command("print")
    @click.option("--rule", "rule_names", type=str, multiple=True)
    def _print(rule_names: t.List[str]) -> None:
        """
        Print the inference rule system.
        """
        printers.print_system(system, renderer)
        print()
        print("Total Number of Rules:", len(system.rules))
        print()

    @_system.command("latexify")
    @click.argument("directory", type=pathlib.Path)
    def _latexify(directory: pathlib.Path) -> None:
        """
        Export the inference rule system to LaTeX.
        """
        assert not directory.exists() or directory.is_dir()
        directory.mkdir(parents=True, exist_ok=True)

        all_rules: t.List[str] = []

        for rule in system.rules:
            source = latex.latexify_rule(rule, renderer)
            all_rules.append(
                f"""
                \\begin{{adjustbox}}{{scale=0.8,max width=.98\\textwidth,center}}
                    $\\displaystyle {source}$
                \\end{{adjustbox}}
                """
            )
            (directory / f"{rule.name}.tex").write_text(source, encoding="utf-8")

        (directory / "all-rules.tex").write_text("\n".join(all_rules), encoding="utf-8")
