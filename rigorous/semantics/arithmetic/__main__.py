# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import click

from ...pretty import console

from .. import cli, sos

from . import parser, semantics


@click.group()
def main() -> None:
    """
    A formal semantics for simple arithmetic expressions.
    """


@main.command()
@click.argument("expression")
@click.option("--print-trees", default=False, is_flag=True)
def explore(expression: str, print_trees: bool = False) -> None:
    initial_state = parser.parse_expression(expression)

    print(
        "Initial State:", console.format_term(initial_state, sos.default_renderer),
    )

    explorer = sos.Explorer(semantics.system)

    print()
    for transition in explorer.iter_transitions(initial_state):
        print()
        print(
            "Source:", console.format_term(transition.source, sos.default_renderer),
        )
        print(
            "Target:", console.format_term(transition.target, sos.default_renderer),
        )
        if print_trees:
            print()
            print(
                console.format_tree(
                    transition.answer.tree, sos.default_renderer, indent=2
                )
            )
        print()


cli.add_system_commands(main, semantics.system, sos.default_renderer)


if __name__ == "__main__":
    main()
