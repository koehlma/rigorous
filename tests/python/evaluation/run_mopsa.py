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
import tempfile

import click

from . import programs


TIMEOUT = 60 * 120  # 120 minutes


@d.dataclass(frozen=True)
class Result:
    identifier: str
    stdout: str
    stderr: str
    returncode: int
    exception: str
    message: str
    timeout: bool = False

    @property
    def was_successful(self) -> bool:
        return self.returncode == 0


def run_test(executable: str, test: programs.TestCase) -> Result:
    with tempfile.TemporaryDirectory(prefix="test_mopsa_") as test_directory:
        test_argument: str
        if test.preamble:
            full_source_file = pathlib.Path(test_directory) / test.path.name
            full_source_file.write_text(test.full_source, encoding="utf-8")
            test_argument = str(full_source_file.resolve())
        else:
            test_argument = str(test.path)
        env = dict(os.environ)
        env["PYTHONPATH"] = str(test.path.parent)
        process = subprocess.Popen(
            [executable, test_argument],
            cwd=test.execution_directory or test.path.parent,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            env=env,
        )
        try:
            returncode = process.wait(TIMEOUT)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            return Result(test.identifier, "", "", -1, "", "", True)
        else:
            assert process.stdout is not None
            stdout = process.stdout.read().decode("utf-8")
            assert process.stderr is not None
            stderr = process.stderr.read().decode("utf-8")
            exception, message = "", ""
            for match in re.finditer(
                r"Uncaught Python exception: (?P<name>\w+)", stdout
            ):
                if not exception or match.group("name") == "AssertionError":
                    exception = match.group("name")
            return Result(
                test.identifier, stdout, stderr, returncode, exception, message, False,
            )


def _run_test(arguments: t.Tuple[str, programs.TestCase]) -> Result:
    return run_test(*arguments)


@click.command()
@click.argument(
    "executable", type=click.Path(exists=True, dir_okay=False, readable=True)
)
@click.argument("report", type=click.Path(dir_okay=False, writable=True))
@click.option(
    "--processes", type=click.IntRange(1), default=2 * multiprocessing.cpu_count()
)
def main(executable: str, report: str, processes: int) -> None:
    print(">>> Running tests on Mopsa")

    pool = multiprocessing.Pool(processes)

    successful_tests = 0

    def status(item: t.Optional[Result] = None) -> str:
        if item is not None:
            return f"{successful_tests} ✔ (last: {item.identifier})"
        return ""

    results: t.Dict[str, t.Any] = {}

    with click.progressbar(
        pool.imap_unordered(
            _run_test, zip(itertools.repeat(executable), programs.all_tests)
        ),
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
            {"type": "Mopsa", "results": results,},
            report_file,
            indent=2,
            ensure_ascii=False,
        )


if __name__ == "__main__":
    main()
