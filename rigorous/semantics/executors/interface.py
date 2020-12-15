# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

import typing as t

from ...core import terms


class Transition(t.Protocol):
    source: terms.Term
    action: terms.Term
    target: terms.Term

    internal_transitions: int


TransitionT = t.TypeVar("TransitionT", bound=Transition, covariant=True)


class Executor(t.Generic[TransitionT]):
    def iter_transitions(self, initial_state: terms.Term) -> t.Iterator[TransitionT]:
        raise NotImplementedError()
