# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import typing as t

import click

from ...core import terms
from ...pretty import console

from .. import cli, sos

from . import parser, pretty, semantics


@click.group()
def main() -> None:
    """
    An executable semantics for the Calculus of Communicating Systems (CCS).
    """


cli.add_system_commands(main, semantics.system, pretty.renderer)


@main.command()
@click.option("--process", "processes", type=(str, str), multiple=True)
@click.option("--print-trees", default=False, is_flag=True)
@click.argument("initial")
def explore(
    initial: str, processes: t.Sequence[t.Tuple[str, str]], print_trees: bool = False,
) -> None:
    """
    Explore the state space of a CCS process.
    """
    initial_state = parser.parse_ccs(initial)
    print("Initial State:", pretty.format_process(initial_state))

    binding: t.Dict[terms.Term, terms.Term] = {}
    for identifier, ccs_term in processes:
        binding[semantics.ProcessVariable(identifier)] = parser.parse_ccs(ccs_term)

    if binding:
        print("\nBinding:")
        for variable, process in binding.items():
            print(
                " ",
                pretty.format_process(variable),
                " := ",
                pretty.format_process(process),
            )

    explorer = sos.Explorer(semantics.system)
    environment = semantics.create_environment(binding)

    print()
    for transition in explorer.iter_transitions(initial_state, environment):
        print()
        print("Source:", pretty.format_process(transition.source))
        print("Action:", pretty.format_process(transition.action))
        print("Target:", pretty.format_process(transition.target))
        if print_trees:
            print()
            print(
                console.format_tree(transition.answer.tree, pretty.renderer, indent=2)
            )
        print()


if __name__ == "__main__":
    main()
