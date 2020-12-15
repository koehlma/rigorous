# -*- coding:utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>

from __future__ import annotations

from ....core import terms

from ... import sos


ACTION_LOAD_LOCAL = terms.symbol("LOAD_LOCAL")
ACTION_STORE_LOCAL = terms.symbol("STORE_LOCAL")
ACTION_DELETE_LOCAL = terms.symbol("DELETE_LOCAL")


def create_load_local(
    identifier: terms.Term, value: terms.Term, default: terms.Term
) -> terms.Term:
    return terms.sequence(ACTION_LOAD_LOCAL, identifier, value, default)


def create_store_local(identifier: terms.Term, value: terms.Term) -> terms.Term:
    return terms.sequence(ACTION_STORE_LOCAL, identifier, value)


def create_delete_local(identifier: terms.Term, value: terms.Term) -> terms.Term:
    return terms.sequence(ACTION_DELETE_LOCAL, identifier, value)


ACTION_CALL = terms.symbol("CALL")
ACTION_YIELD = terms.symbol("YIELD")
ACTION_RETURN = terms.symbol("RETURN")
ACTION_THROW = terms.symbol("THROW")
ACTION_RESULT = terms.symbol("RESULT")
ACTION_ERROR = terms.symbol("ERROR")
ACTION_VALUE = terms.symbol("VALUE")
ACTION_SEND_VALUE = terms.symbol("SEND_VALUE")
ACTION_SEND_THROW = terms.symbol("SEND_THROW")


def create_call(frame: terms.Term) -> terms.Term:
    return terms.sequence(ACTION_CALL, frame)


def create_yield(value: terms.Term) -> terms.Term:
    return terms.sequence(ACTION_YIELD, value)


def create_return(value: terms.Term) -> terms.Term:
    return terms.sequence(ACTION_RETURN, value)


def create_throw(exception: terms.Term) -> terms.Term:
    return terms.sequence(ACTION_THROW, exception)


def create_result(value: terms.Term) -> terms.Term:
    return terms.sequence(ACTION_RESULT, value)


def create_error(exception: terms.Term) -> terms.Term:
    return terms.sequence(ACTION_ERROR, exception)


def create_value(frame: terms.Term, value: terms.Term) -> terms.Term:
    return terms.sequence(ACTION_VALUE, frame, value)


def create_send_value(frame: terms.Term, value: terms.Term) -> terms.Term:
    return terms.sequence(ACTION_SEND_VALUE, frame, value)


def create_send_throw(frame: terms.Term, value: terms.Term) -> terms.Term:
    return terms.sequence(ACTION_SEND_THROW, frame, value)


ACTION_MEM_LOAD = terms.symbol("MEM_LOAD")
ACTION_MEM_NEW = terms.symbol("MEM_NEW")
ACTION_MEM_STORE = terms.symbol("MEM_STORE")


def create_mem_load(reference: terms.Term, value: terms.Term) -> terms.Term:
    return terms.sequence(ACTION_MEM_LOAD, reference, value)


def create_mem_new(reference: terms.Term, value: terms.Term) -> terms.Term:
    return terms.sequence(ACTION_MEM_NEW, reference, value)


def create_mem_store(reference: terms.Term, value: terms.Term) -> terms.Term:
    return terms.sequence(ACTION_MEM_STORE, reference, value)


ACTION_PRINT = terms.symbol("PRINT")


def create_print(value: terms.Term) -> terms.Term:
    return terms.sequence(ACTION_PRINT, value)


ACTION_GET_ACTIVE_EXC = terms.symbol("GET_ACTIVE_EXC")


def create_get_active_exc(value: terms.Term) -> terms.Term:
    return terms.sequence(ACTION_GET_ACTIVE_EXC, value)


ACTION_BREAK = terms.symbol("BREAK")
ACTION_CONTINUE = terms.symbol("CONTINUE")


is_terminating_action = sos.build_is_action_operator(
    "is_terminating", {ACTION_BREAK, ACTION_CONTINUE, ACTION_THROW, ACTION_RETURN},
)

is_throw_action = sos.build_is_action_operator("is_throw", {ACTION_THROW})

is_get_exc_action = sos.build_is_action_operator(
    "is_get_active_exc", {ACTION_GET_ACTIVE_EXC}
)

is_loop_action = sos.build_is_action_operator(
    "is_loop", {ACTION_BREAK, ACTION_CONTINUE}
)

is_memory_action = sos.build_is_action_operator(
    "is_memory", {ACTION_MEM_LOAD, ACTION_MEM_STORE, ACTION_MEM_NEW},
)

is_stack_action = sos.build_is_action_operator(
    "is_stack",
    {
        ACTION_CALL,
        ACTION_YIELD,
        ACTION_RETURN,
        ACTION_THROW,
        ACTION_RESULT,
        ACTION_ERROR,
        ACTION_VALUE,
        ACTION_SEND_VALUE,
        ACTION_SEND_THROW,
    },
)

is_frame_action = sos.build_is_action_operator(
    "is_frame", {ACTION_LOAD_LOCAL, ACTION_STORE_LOCAL, ACTION_DELETE_LOCAL}
)
