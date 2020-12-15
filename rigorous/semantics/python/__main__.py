# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import dataclasses as d
import typing as t

import enum
import pathlib
import time

import click

from ...core import terms, unification
from ...data import mappings, references, strings, records, numbers, tuples
from ...pretty import console, latex

from .. import cli, sos

from .rules import actions, frames, memory, stack
from .syntax import parser
from .basis import primitives, macros
from . import sugar

from ..executors import bottom_up, engine, interface

from . import bootstrap, pretty, semantics, sugar, runtime


@click.group()
def main() -> None:
    """
    A rigorous formal semantics for Python.
    """
    pass


cli.add_system_commands(main, semantics.system, pretty.renderer)


class ResultKind(enum.Enum):
    UNSUPPORTED_SYNTAX = "unsupported-syntax"
    REMAINING_CODE = "remaining-code"
    SUCCESSFULL = "successfull"
    NO_TRANSITIONS = "no-transitions"
    EXCEPTION_THROWN = "exception-thrown"


@d.dataclass(frozen=True)
class TestResult:
    test: pathlib.Path
    kind: ResultKind
    error: t.Optional[str] = None


_THROW_EXCEPTION = terms.variable("exception")
_THROW_PATTERN = actions.create_throw(_THROW_EXCEPTION)


def unwrap_throw(action: terms.Term) -> t.Optional[terms.Term]:
    match = unification.match(_THROW_PATTERN, action)
    if match:
        return match[_THROW_EXCEPTION]
    else:
        return None


def is_done_state(state: terms.Term) -> bool:
    var_memory = terms.variable("memory")
    return bool(
        unification.match(
            memory.create_memory_layer(
                var_memory, stack.create_stack_layer(stack.STACK_NIL),
            ),
            state,
        )
    )


def unwrap_memory(state: terms.Term) -> t.Tuple[mappings.Mapping, terms.Term]:
    var_memory = terms.variable("memory")
    var_inner = terms.variable("inner")
    match = unification.match(memory.create_memory_layer(var_memory, var_inner), state)
    assert match
    x = match[var_memory]
    assert isinstance(x, mappings.Mapping)
    return x, match[var_inner]


def run_test(test: pathlib.Path) -> TestResult:
    try:
        module = parser.parse_module(test.read_text(encoding="utf-8"))
    except parser.UnsupportedSyntaxError:
        return TestResult(test, ResultKind.UNSUPPORTED_SYNTAX)

    translator = bootstrap.create_translator()

    try:
        module_term = translator.translate_module(module)
    except NotImplementedError:
        return TestResult(test, ResultKind.UNSUPPORTED_SYNTAX)

    global_namespace = translator.heap_builder.new_mapping_proxy()
    local_namespace = mappings.create(
        {
            strings.create("__globals__"): global_namespace,
            strings.create("__cells__"): mappings.EMPTY,
        }
    )

    module_frame = frames.create_frame_layer(
        records.create(locals=local_namespace, body=module_term)
    )

    initial_state = memory.create_memory_layer(
        translator.heap_builder.heap, stack.initialize_stack(module_frame)
    )

    last_state: t.Optional[terms.Term] = None

    for transition in semantics.executor.iter_transitions(initial_state):
        last_state = transition.target
        exception = unwrap_throw(transition.action)
        if exception:
            mem, inner = unwrap_memory(transition.target)
            exc_name = mem[mem[exception].getfield("cls")].getfield("name").value  # type: ignore
            return TestResult(test, ResultKind.EXCEPTION_THROWN, exc_name)

    if last_state is None:
        return TestResult(test, ResultKind.NO_TRANSITIONS)

    if is_done_state(last_state):
        return TestResult(test, ResultKind.SUCCESSFULL)
    else:
        return TestResult(test, ResultKind.REMAINING_CODE)


@main.command()
@click.argument("directory", type=pathlib.Path)
def latexify_sugar(directory: pathlib.Path) -> None:
    for name, term in sugar.SUGAR.items():
        tex_file = directory / f"{name}.tex"
        tex_file.write_text(latex.latexify_term(term, pretty.renderer))


@main.command()
@click.argument("directory", type=pathlib.Path)
def latexify_rule_table(directory: pathlib.Path) -> None:
    pass


@main.group()
def latexify() -> None:
    """
    Export various aspects of the semantics to LaTeX.
    """


_TERM_TYPE_TO_LATEX = {
    terms.Term: r"\mathcal{T}",
    numbers.Number: r"\mathit{Num}",
    numbers.Integer: r"\mathit{Int}",
    strings.String: r"\mathit{Str}",
    records.Record: r"\mathit{Rec}",
    mappings.Mapping: r"\mathit{Map}",
    references.Reference: r"\mathit{Ref}",
    tuples.Tuple: r"\mathit{Vec}",
}


@latexify.command("primitives")
@click.argument("output", type=pathlib.Path)
def latexify_primitives(output: pathlib.Path) -> None:
    """
    Generates a listing of all primitives.
    """

    lines: t.List[str] = []

    for primitive in primitives.get_primitives().values():
        lines.append("\\begin{mdframed}[nobreak=true]")
        name = f"\\texttt{{{latex.latex_escape(primitive.name)}}}"
        parameter_types = r" \times ".join(
            _TERM_TYPE_TO_LATEX.get(typ, typ.__name__)
            for typ in primitive.parameter_types
        )
        return_type = _TERM_TYPE_TO_LATEX.get(
            primitive.return_type, primitive.return_type.__name__
        )
        filename = pathlib.Path(primitive.location.filename).name
        lineno = primitive.location.lineno
        location = f"\\texttt{{{filename}:{lineno}}}"
        lines.append(
            f"${name}: {parameter_types} \\to {return_type}$ \\hfill {location} \\\\[-.7em]"
        )
        lines.append("\\hrule")
        lines.append(primitive.description)
        lines.append("\\end{mdframed}")

    output.write_text("\n".join(lines), encoding="utf-8")


@latexify.command("macros")
@click.argument("output", type=pathlib.Path)
def latexify_macros(output: pathlib.Path) -> None:
    """
    Generates a listing of all macros.
    """

    lines: t.List[str] = []

    for name, macro in macros.get_macros().items():
        lines.append("\\begin{mdframed}[nobreak=true]")
        name = f"\\texttt{{{latex.latex_escape(name)}}}"

        filename = pathlib.Path(macro.__code__.co_filename).name
        lineno = macro.__code__.co_firstlineno

        location = f"\\texttt{{{filename}:{lineno}}}"
        lines.append(f"{name} \\hfill {location} \\\\[-.7em]")
        lines.append("\\hrule")
        lines.append(macro.__doc__ or "")
        lines.append("\\end{mdframed}")

    output.write_text("\n".join(lines), encoding="utf-8")


@latexify.command("runtime")
@click.argument("output", type=pathlib.Path)
def latexify_runtime(output: pathlib.Path) -> None:
    """
    Generates a listing of all runtime functions.
    """

    lines: t.List[str] = []

    for name, function in runtime.get_runtime_functions().items():
        if function.docstring is None:
            continue
        lines.append("\\begin{mdframed}[nobreak=true]")
        parameters = ", ".join(function.parameters)
        name = f"\\texttt{{{latex.latex_escape(name)}({parameters})}}"
        location = f"\\texttt{{runtime.py:{function.lineno}}}"
        lines.append(f"{name} \\\\ \\hfill {location} \\\\[-.7em]")
        lines.append("\\hrule")
        lines.append(function.docstring or "")
        lines.append("\\end{mdframed}")

    output.write_text("\n".join(lines), encoding="utf-8")


_executors: t.Mapping[str, interface.Executor[interface.Transition]] = {
    "INFERENCE_ENGINE": engine.Executor(semantics.system),
    "BOTTOM_UP": semantics.create_executor(shortcircuit=True),
    "BUTTOM_UP_NO_SHORTCIRCUIT": semantics.create_executor(shortcircuit=False),
}


@main.command()
@click.option(
    "--executor",
    "executor_name",
    type=click.Choice(_executors.keys()),
    default="BOTTOM_UP",
)
@click.argument("filename", type=click.Path(dir_okay=False, readable=True))
def run_module(executor_name: str, filename: str) -> None:
    """
    Executes a single module without imports.
    """
    module_code = pathlib.Path(filename).read_text(encoding="utf-8")
    module = parser.parse_module(module_code)

    translator = bootstrap.create_translator()

    module_term = translator.translate_module(module)

    print(console.format_term(module_term, pretty.renderer))

    global_namespace = translator.heap_builder.new_mapping_proxy()
    local_namespace = mappings.create(
        {
            strings.create("__globals__"): global_namespace,
            strings.create("__cells__"): mappings.EMPTY,
        }
    )

    module_frame = frames.create_frame_layer(
        records.create(locals=local_namespace, body=module_term)
    )

    initial_state = memory.create_memory_layer(
        translator.heap_builder.heap, stack.initialize_stack(module_frame)
    )

    executor = _executors[executor_name]

    last_transition: t.Optional[interface.Transition] = None

    start_time = time.monotonic()

    transitions = 0

    try:
        for transition in executor.iter_transitions(initial_state):
            if transition.action != sos.ACTION_TAU:
                print(
                    "Action:", console.format_term(transition.action, pretty.renderer),
                )
            last_transition = transition
            transitions += transition.internal_transitions
    except bottom_up.NonDeterminismError as e:
        print("Non determinism in state:")
        print(console.format_term(unwrap_memory(e.state)[1], pretty.renderer),)
        print("=" * 80)

    end_time = time.monotonic()

    if last_transition is not None:
        heap_data, inner = unwrap_memory(last_transition.target)
        print(console.format_term(inner, pretty.renderer),)
        exception = unwrap_throw(last_transition.action)
        if exception:
            print(
                "Exception:",
                console.format_term(heap_data.entries[exception], pretty.renderer),
            )
        else:
            print("Ok!")
    else:
        print("No last transition!")

    print()
    print(f"Time: {end_time - start_time:.3f}")
    print(f"Transitions: {transitions}")


if __name__ == "__main__":
    main()
