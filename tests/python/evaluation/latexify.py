# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import typing as t

import collections
import enum
import json
import pathlib
import statistics

import click

from rigorous.pretty.latex import latex_escape

from . import programs


class Mark(enum.Enum):
    SUCCESS = r"\textcolor{koehlma-green}{\checkmark}"
    ASSERTION = r"\textcolor{koehlma-red}{X}"
    EXCEPTION = r"\textcolor{koehlma-yellow}{--}"
    TIMEOUT = r"\textcolor{gray}{T}"
    UNSUPPORTED = r"\textcolor{gray}{U}"
    PANIC = r"\textcolor{gray}{P}"


def get_mark(result: t.Any) -> Mark:
    if result["returncode"] == 0:
        return Mark.SUCCESS
    elif result["exception"] == "AssertionError":
        return Mark.ASSERTION
    elif (
        result["stderr"] == "Unsupported Syntax!"
        or "Uncaught exception: Failure" in result["stdout"]
    ):
        return Mark.UNSUPPORTED
    elif "panic in" in result["stdout"]:
        return Mark.PANIC
    elif result["timeout"]:
        return Mark.TIMEOUT
    else:
        return Mark.EXCEPTION


def count_marks(results: t.Mapping[str, t.Any]) -> t.Mapping[Mark, int]:
    counter: t.MutableMapping[Mark, int] = collections.Counter()
    for result in results.values():
        counter[get_mark(result)] += 1
    return counter


@click.command()
@click.argument("reports", type=click.Path(file_okay=False))
@click.argument("output", type=click.Path(dir_okay=False, writable=True))
def main(reports: str, output: str) -> None:
    """
    Generates a LaTeX table from the test reports.
    """
    json_reports = {
        path: json.loads(path.read_text(encoding="utf-8"))
        for path in pathlib.Path(reports).resolve().glob("*.json")
    }

    cpython_results: t.Dict[str, t.Dict[str, t.Any]] = {}
    mopsa_results: t.Dict[str, t.Any] = {}
    lambda_py_results: t.Dict[str, t.Any] = {}
    sos_python_results: t.Dict[str, t.Any] = {}

    for report in json_reports.values():
        if report["type"] == "CPython":
            cpython_results[report["version"]] = report["results"]
        elif report["type"] == "Lambda-Py":
            lambda_py_results = report["results"]
        elif report["type"] == "Mopsa":
            mopsa_results = report["results"]
        else:
            assert report["type"] == "SOS"
            sos_python_results = report["results"]

    cpython_versions = list(cpython_results.keys())
    cpython_versions.sort()

    assert cpython_results, "results for CPython are missing"
    assert lambda_py_results, "results for Lambda-Py are missing"
    assert mopsa_results, "results for Mopsa are missing"
    assert sos_python_results, "results for SOS Python are missing"

    num_columns = 1 + len(cpython_results) + 1 + 1 + 3

    lines: t.List[str] = [
        f"\\begin{{longtable}}{{|r|{len(cpython_results) * 'c'}|c|c|ccc|}}\\hline",
        f"& \\multicolumn{{{len(cpython_results)}}}{{c|}}{{CPython}}",
        "& $\\lambda_\\pi$ & \\Mopsa & \\multicolumn{3}{c|}{SOS Python} \\\\",
        f"& {'&'.join(cpython_versions)} & & & & Time $[s]$ & Transitions \\\\",
        "\\hline\\endhead",
    ]

    columns: t.List[str] = [""]

    sos_python_times: t.List[float] = []
    sos_python_transitions: t.List[int] = []

    for test in programs.all_tests:
        columns.clear()
        columns.append(f"{latex_escape(test.name)}")

        for version in cpython_versions:
            columns.append(get_mark(cpython_results[version][test.identifier]).value)

        columns.append(get_mark(lambda_py_results[test.identifier]).value)
        columns.append(get_mark(mopsa_results[test.identifier]).value)

        sos_result = sos_python_results[test.identifier]
        columns.append(get_mark(sos_result).value)
        if sos_result["returncode"] == 0:
            columns.append(f"${sos_result['execution_time']:.2f}$")
            columns.append(f"${sos_result['transitions']:,}$".replace(",", "\\,"))
            sos_python_times.append(sos_result["execution_time"])
            sos_python_transitions.append(sos_result["transitions"])
        else:
            columns.append(r"\textcolor{gray}{--}")
            columns.append(r"\textcolor{gray}{--}")

        lines.append("&".join(columns))
        lines.append("\\\\")

    lines.append("\\hline \\hline")

    cpython_statistics = {
        version: count_marks(results) for version, results in cpython_results.items()
    }
    lambda_py_statistics = count_marks(lambda_py_results)
    mopsa_statistics = count_marks(mopsa_results)
    sos_python_statistics = count_marks(sos_python_results)

    for mark in Mark:
        columns.clear()
        columns.append(mark.value)
        for version in cpython_versions:
            columns.append(str(cpython_statistics[version][mark]))
        columns.append(str(lambda_py_statistics[mark]))
        columns.append(str(mopsa_statistics[mark]))
        columns.append(
            f"\\multicolumn{{3}}{{c|}}{{{str(sos_python_statistics[mark])}}}"
        )
        lines.append("&".join(columns))
        lines.append("\\\\")
    lines.append("\\hline")
    lines.append(
        f"\\multicolumn{{{num_columns}}}{{c}}"
        "{\\rule{0pt}{1.2\\normalbaselineskip}Generated by \\texttt{evaluation/latexify.py}.}"
    )
    lines.append("\\end{longtable}")

    pathlib.Path(output).write_text("\n".join(lines), encoding="utf-8")

    num_k_python_tests = sum(1 for test in programs.all_tests if test.is_k_python)
    num_lambda_py_tests = sum(1 for test in programs.all_tests if test.is_lambda_py)
    print("Total number of tests:", len(programs.all_tests))
    print("K Python tests:", num_k_python_tests)
    print("Lambda-Py tests:", num_lambda_py_tests)
    print(
        "Our tests:", len(programs.all_tests) - num_k_python_tests - num_lambda_py_tests
    )
    print(f"Median Time: {statistics.median(sos_python_times)}")
    print(f"Median Transitions: {statistics.median(sos_python_transitions)}")
    print(f"AVG Time: {statistics.mean(sos_python_times)}")
    print(f"AVG Transitions: {statistics.mean(sos_python_transitions)}")


if __name__ == "__main__":
    main()
