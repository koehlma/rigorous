# -*- coding: utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import typing as t

import pathlib
import subprocess

import click


PRELUDE_HEAD = f"""
# -*- coding: utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>
#
# This file has been automatically generated by:
# `python -m {__package__} generate-prelude`
# 
# Do not modify this file manually!
#
# type: ignore
# flake8: noqa


raise AssertionError("this file should never be imported")


SENTINEL = ...

BUILTINS = ...

code = ...
function = ...

mappingproxy = ...

ellipsis = ...

NoneType = ...
""".strip()


@click.group()
def main() -> None:
    pass


@main.command()
def generate_prelude() -> None:
    """
    Generates the prelude file for the runtime and builtin definitions.
    """

    prelude_file = (pathlib.Path(__file__).parent / "source" / "prelude.py").resolve()
    print(f"Prelude File: {prelude_file.relative_to(pathlib.Path.cwd())}")

    lines: t.List[str] = ["\n\n"]

    from . import macros, primitives

    lines.append("# Macros")
    for name in sorted(macros.get_macros()):
        lines.append(f"{name} = ...")

    lines.append("\n# Primitives")
    for name in sorted(primitives.get_primitives()):
        lines.append(f"{name} = ...")

    print("Writing...")
    prelude_file.write_text(PRELUDE_HEAD + "\n".join(lines), encoding="utf-8")

    print("Formatting...")
    subprocess.check_call(["black", prelude_file])

    print("Done!")


if __name__ == "__main__":
    main()
