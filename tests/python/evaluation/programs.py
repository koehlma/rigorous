# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import dataclasses as d
import typing as t

import functools
import pathlib


@d.dataclass(frozen=True)
class TestCase:
    identifier: str
    path: pathlib.Path

    preamble: str = ""

    execution_directory: t.Optional[pathlib.Path] = None

    @property
    def name(self) -> str:
        if "k-python" in self.path.parts:
            return f"k-python/{self.path.name}"
        elif "lambda-py" in self.path.parts:
            return f"lambda-py/{self.path.name}"
        else:
            return self.identifier

    @property
    def is_k_python(self) -> bool:
        return "k-python" in self.path.parts

    @property
    def is_lambda_py(self) -> bool:
        return "lambda-py" in self.path.parts

    @functools.cached_property
    def raw_source(self) -> str:
        return self.path.read_text(encoding="utf-8")

    @functools.cached_property
    def full_source(self) -> str:
        return self.preamble + self.raw_source


LAMBDA_PY_PREAMBLE = """
def ___assertEqual(self, other):
    assert self == other, (self, other)


def ___fail(msg=""):
    raise AssertionError(msg)


def ___assertFail(msg=""):
    assert False, msg


def ___assertFalse(self):
    assert not self, self


def ___assertIn(self, other):
    assert self in other, (self, other)


def ___assertIs(self, other):
    assert self is other, (self, other)


def ___assertIsNot(self, other):
    assert self is not other, (self, other)


def ___assertNotEqual(self, other):
    assert self != other, (self, other)


def ___assertNotIn(self, other):
    assert self not in other, (self, other)


def ___assertTrue(self):
    assert self, self


def ___assertRaises(self, func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except self:
        return
    else:
        assert False, "did not raise exception"
"""


programs_directory = (pathlib.Path(__file__).parent / ".." / "programs").resolve()


def _from_path(
    path: pathlib.Path,
    preamble: str = "",
    execution_directory: t.Optional[pathlib.Path] = None,
) -> TestCase:
    return TestCase(
        str("/".join(path.relative_to(programs_directory).parts)),
        path,
        preamble,
        execution_directory,
    )


original_k_python_tests = tuple(
    map(
        lambda path: _from_path(
            path, execution_directory=programs_directory / "original" / "k-python"
        ),
        (programs_directory / "original" / "k-python").glob("**/test*.py"),
    )
)
original_lambda_py_tests = tuple(
    map(
        lambda path: _from_path(path, LAMBDA_PY_PREAMBLE),
        (programs_directory / "original" / "lambda-py").glob("**/*.py"),
    )
)

modified_tests = tuple(
    map(_from_path, (programs_directory / "modified").glob("**/*.py"))
)

our_tests = tuple(map(_from_path, (programs_directory / "koehl").glob("**/*.py")))


all_tests = (
    original_k_python_tests + original_lambda_py_tests + modified_tests + our_tests
)
