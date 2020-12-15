# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import dataclasses as d
import typing as t

import itertools
import multiprocessing
import os
import pathlib
import re
import subprocess
import stopit
import tempfile
import threading
import time

import click

from . import programs

from rigorous.core import terms, unification
from rigorous.data import mappings, strings, records

from rigorous.semantics.python.syntax import parser
from rigorous.semantics.python import bootstrap, semantics
from rigorous.semantics.python.rules import frames, memory, stack, actions


TIMEOUT = 60 * 120  # 2 hours


@d.dataclass(frozen=True)
class Result:
    identifier: str
    stdout: str
    stderr: str
    returncode: int
    exception: str
    message: str

    timeout: bool = False

    execution_time: float = -1
    transitions: int = 0

    @property
    def was_successful(self) -> bool:
        return self.returncode == 0


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


def run_test(test: programs.TestCase) -> Result:
    try:
        module = parser.parse_module(test.raw_source)
    except parser.UnsupportedSyntaxError:
        return Result(
            test.identifier,
            stdout="",
            stderr="Unsupported Syntax!",
            returncode=1,
            exception="",
            message="",
        )

    translator = bootstrap.create_translator()

    try:
        module_term = translator.translate_module(module)
    except NotImplementedError:
        return Result(
            test.identifier,
            stdout="",
            stderr="Unsupported Syntax!",
            returncode=1,
            exception="",
            message="",
        )

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

    start_time = time.monotonic()

    transitions = 0

    with stopit.ThreadingTimeout(TIMEOUT) as timeout_mgr:
        for transition in semantics.executor.iter_transitions(initial_state):
            last_state = transition.target
            transitions += transition.internal_transitions
            exception = unwrap_throw(transition.action)
            if exception:
                mem, inner = unwrap_memory(transition.target)
                exc_name = mem[mem[exception].getfield("cls")].getfield("name").value
                return Result(
                    test.identifier,
                    stdout="",
                    stderr=f"{exc_name}:",
                    returncode=1,
                    exception=exc_name,
                    message="",
                )

    if timeout_mgr.state == timeout_mgr.TIMED_OUT:
        print(f"Timeout {test.identifier}")
        return Result(
            test.identifier,
            stdout="",
            stderr=f"Timeout!",
            returncode=1,
            exception="",
            message="",
            timeout=True,
        )

    end_time = time.monotonic()

    if last_state is None:
        return Result(
            test.identifier,
            stdout="",
            stderr="No Transitions!",
            returncode=1,
            exception="",
            message="",
        )

    if is_done_state(last_state):
        return Result(
            test.identifier,
            stdout="",
            stderr="",
            returncode=0,
            exception="",
            message="",
            execution_time=end_time - start_time,
            transitions=transitions,
        )
    else:
        return Result(
            test.identifier,
            stdout="",
            stderr="Remaining Code!",
            returncode=1,
            exception="",
            message="",
        )


@click.command()
@click.argument("report", type=click.Path(dir_okay=False, writable=True))
@click.option(
    "--processes", type=click.IntRange(1), default=2 * multiprocessing.cpu_count()
)
def main(report: str, processes: int) -> None:
    print(">>> Running tests on SOS Python")

    pool = multiprocessing.Pool(processes)

    successful_tests = 0

    def status(item: t.Optional[Result] = None) -> str:
        if item is not None:
            return f"{successful_tests} ✔ (last: {item.identifier})"
        return ""

    results: t.Dict[str, t.Any] = {}

    with click.progressbar(
        pool.imap_unordered(run_test, programs.all_tests),
        show_pos=True,
        show_eta=False,
        length=len(programs.all_tests),
        item_show_func=status,
    ) as bar:
        for result in bar:
            if result.was_successful:
                successful_tests += 1
            results[result.identifier] = d.asdict(result)

    print(f">>> Successful tests: {successful_tests}")

    import json

    with open(report, "wt", encoding="utf-8") as report_file:
        json.dump(
            {"type": "SOS", "results": results,},
            report_file,
            indent=2,
            ensure_ascii=False,
        )


if __name__ == "__main__":
    main()
