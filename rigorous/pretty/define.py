# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import dataclasses as d
import typing as t

import inspect

from mxu.maps import IdentityMap

from ..core import inference, terms


@d.dataclass(frozen=True)
class LocationInfo:
    filename: str
    lineno: int


@d.dataclass(eq=False)
class Group:
    name: str
    rules: t.List[inference.Rule] = d.field(default_factory=list)
    description: t.Optional[str] = None
    location: t.Optional[LocationInfo] = None

    def add_to_system(self, system: inference.System) -> None:
        for rule in self.rules:
            system.add_rule(rule)

    def define_rule(
        self,
        name: str,
        conclusion: terms.Term,
        premises: inference.Premises = (),
        constraints: inference.Constraints = (),
        conditions: inference.Conditions = (),
        *,
        description: t.Optional[str] = None,
        frame_index: int = 0
    ) -> inference.Rule:
        return rule(
            name=name,
            conclusion=conclusion,
            premises=premises,
            constraints=constraints,
            conditions=conditions,
            group=self,
            description=description,
            frame_index=frame_index + 1,
        )


@d.dataclass(eq=False)
class VariableInfo:
    variable: terms.Variable
    text: t.Optional[str] = None
    math: t.Optional[str] = None
    description: t.Optional[str] = None
    location: t.Optional[LocationInfo] = None


@d.dataclass(eq=False)
class RuleInfo:
    rule: inference.Rule
    group: t.Optional[Group] = None
    description: t.Optional[str] = None
    location: t.Optional[LocationInfo] = None


_variable_info: IdentityMap[terms.Variable, VariableInfo] = IdentityMap()

_rule_info: IdentityMap[inference.Rule, RuleInfo] = IdentityMap()


def get_location_info(frame_index: int = 2) -> LocationInfo:
    frame_info = inspect.stack()[frame_index]
    return LocationInfo(frame_info.filename, frame_info.lineno)


def variable(
    name: str,
    *,
    text: t.Optional[str] = None,
    math: t.Optional[str] = None,
    description: t.Optional[str] = None
) -> terms.Variable:
    variable = terms.variable(name)
    info = VariableInfo(
        variable,
        text=text,
        math=math,
        description=description,
        location=get_location_info(),
    )
    _variable_info[variable] = info
    return variable


def get_variable_info(variable: terms.Variable) -> t.Optional[VariableInfo]:
    return _variable_info.get(variable, None)


def rule(
    name: str,
    conclusion: terms.Term,
    premises: inference.Premises = (),
    constraints: inference.Constraints = (),
    conditions: inference.Conditions = (),
    *,
    group: t.Optional[Group] = None,
    description: t.Optional[str] = None,
    frame_index: int = 0
) -> inference.Rule:
    rule = inference.Rule(
        name=name,
        conclusion=conclusion,
        premises=premises,
        constraints=constraints,
        conditions=conditions,
    )
    if group is not None:
        group.rules.append(rule)
    info = RuleInfo(
        rule,
        group=group,
        description=description,
        location=get_location_info(frame_index + 2),
    )
    _rule_info[rule] = info
    return rule


def get_rule_info(rule: inference.Rule) -> t.Optional[RuleInfo]:
    return _rule_info.get(rule, None)


def group(name: str, *, description: t.Optional[str] = None) -> Group:
    return Group(name, description=description, location=get_location_info())
