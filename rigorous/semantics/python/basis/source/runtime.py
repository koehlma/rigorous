# -*- coding: utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>
#
# type: ignore
# flake8: noqa

"""
The runtime functions of the formal semantics are defined here.
"""

from .builtins import *
from .prelude import *

raise AssertionError("this file should never be imported")


# region: Cells and Closures


class Cell:
    def __init__(self):
        self.__value__ = SENTINEL

    def set_value(self, value):
        self.__value__ = value

    def get_value(self):
        if self.__value__ is SENTINEL:
            raise NameError()
        else:
            return self.__value__

    def delete_value(self):
        self.__value__ = SENTINEL


def store_cell(cells, identifier, value):
    r"""
    Stores a value in the cell of the closure \verb!cells!.
    """
    mapping_get(cells, identifier).set_value(value)


def load_cell(cells, identifier):
    r"""
    Loads a value from the cell of the closure \verb!cells!.
    """
    return mapping_get(cells, identifier).get_value()


def load__class__(cells):
    r"""
    Loads the special cell \verb!__class__! from the closure \verb!cells!.
    """
    try:
        cls = mapping_get(cells, LITERAL("__class__")).get_value()
        if not lowlevel_isinstance(cls, type):
            raise SystemError()
        return cls
    except NameError:
        raise SystemError()


def delete_cell(cells, identifier):
    r"""
    Deletes the value in the cell of the closure \verb!cells!.
    """
    mapping_get(cells, identifier).delete_value()


def class_super(cls, instance):
    r"""
    Used to implement \verb!super! without any arguments.
    """
    if instance is None:
        raise SystemError()
    return super(cls, instance)


# endregion


# region: Tuples and Lists


class list_iterator:
    def __init__(self, __list__):
        self.__list__ = __list__
        self.__index__ = 0
        self.__length__ = len(__list__)

    def __iter__(self):
        return self

    def __next__(self):
        index = self.__index__
        if index < self.__length__:
            element = self.__list__[index]
            self.__index__ = index + 1
            return element
        else:
            raise StopIteration()


class tuple_iterator:
    def __iter__(self):
        return self

    def __next__(self):
        self_value = VALUE_OF(self)
        index = record_get(self_value, LITERAL("index"))
        sequence = record_get(self_value, LITERAL("sequence"))
        if index < sequence_length(sequence):
            SET_VALUE(
                self,
                record_set(self_value, LITERAL("index"), number_add(index, LITERAL(1))),
            )
            return sequence_get(sequence, index)
        else:
            raise StopIteration()


def make_list(elements):
    """
    Constructs a list from the provided vector of elements.
    """
    return NEW_FROM_VALUE(list, elements)


def make_tuple(elements):
    """
    Constructs a tuple from the provided vector of arguments.
    """
    return NEW_FROM_VALUE(tuple, elements)


def runtime_sequence_equals(this, that):
    length = sequence_length(this)
    if length != sequence_length(that):
        return False
    index = LITERAL(0)
    while index < length:
        self_element = sequence_get(this, index)
        other_element = sequence_get(that, index)
        if self_element != other_element:
            return False
        index = number_add(index, LITERAL(1))
    return True


def runtime_sequence_get(sequence, index):
    if number_neg(sequence_length(sequence)) <= index < sequence_length(sequence):
        return sequence_get(sequence, index)
    else:
        raise IndexError()


def runtime_sequence_set(sequence, index, value):
    if number_neg(sequence_length(sequence)) <= index < sequence_length(sequence):
        return sequence_set(sequence, index, value)
    else:
        raise IndexError()


# endregion


# region: Dictionaries and Mappings


def make_dict(entries):
    """
    Constructs a dict from the provided vector of entries.
    """
    result = NEW_FROM_VALUE(dict, LITERAL(()))
    index = LITERAL(0)
    length = sequence_length(entries)
    while index < length:
        entry = sequence_get(entries, index)
        result[sequence_get(entry, LITERAL(0))] = sequence_get(entry, LITERAL(1))
        index = number_add(index, LITERAL(1))
    return result


class DictKeyIterator:
    def __iter__(self):
        return self

    def __next__(self):
        self_value = VALUE_OF(self)
        index = record_get(self_value, LITERAL("index"))
        sequence = record_get(self_value, LITERAL("entries"))
        if index < sequence_length(sequence):
            SET_VALUE(
                self,
                record_set(self_value, LITERAL("index"), number_add(index, LITERAL(1))),
            )
            return record_get(sequence_get(sequence, index), LITERAL("key"))
        else:
            raise StopIteration()


def dict_find_entry(self, key, key_hash):
    index = LITERAL(0)
    entries = VALUE_OF(self)
    length = sequence_length(entries)
    while index < length:
        entry = sequence_get(entries, index)
        if record_get(entry, LITERAL("hash")) == key_hash:
            if record_get(entry, LITERAL("key")) == key:
                return index
        index = number_add(index, LITERAL(1))


class MappingItemsIterator:
    def __init__(self, mapping):
        self.__mapping__ = mapping
        self.__keys__ = iter(mapping)

    def __iter__(self):
        return self

    def __next__(self):
        key = next(self.__keys__)
        return NEW_FROM_VALUE(tuple, LITERAL((key, self.__mapping__[key])))


class MappingProxyIterator:
    def __init__(self, mapping):
        self.__mapping__ = mapping
        self.__keys__ = mapping_keys(mapping)
        self.__length__ = sequence_length(self.__keys__)
        self.__index__ = LITERAL(0)

    def __iter__(self):
        return self

    def __next__(self):
        if self.__index__ < self.__length__:
            key = sequence_get(self.__keys__, self.__index__)
            self.__index__ = number_add(self.__index__, LITERAL(1))
        else:
            raise StopIteration()


class mappingproxy:
    def items(self):
        return MappingItemsIterator(self)

    def __iter__(self):
        return MappingProxyIterator(VALUE_OF(self))

    def __getitem__(self, key):
        key_value = VALUE_OF(key)
        self_value = VALUE_OF(self)
        if mapping_contains(self_value, key_value):
            return mapping_get(self_value, key_value)
        raise KeyError()

    def __setitem__(self, key, value):
        key_value = VALUE_OF(key)
        self_value = VALUE_OF(self)
        SET_VALUE(self, mapping_set(self_value, key_value, value))

    def __delitem__(self, key):
        # raise TypeError()
        key_value = VALUE_OF(key)
        self_value = VALUE_OF(self)
        if mapping_contains(self_value, key_value):
            SET_VALUE(self, mapping_delete(self_value, key_value))
        else:
            raise KeyError()

    def __contains__(self, key):
        key_value = VALUE_OF(key)
        self_value = VALUE_OF(self)
        if mapping_contains(self_value, key_value):
            return True
        return False


# endregion


# region: Object Auxillary Descriptors and Functions


class ClassDescriptor:
    def __get__(self, instance, owner=None):
        if instance is None:
            return CLS_OF(owner)
        elif instance is SENTINEL:
            # access of `__class__` on None
            return NoneType
        else:
            return CLS_OF(instance)


class DictDescriptor:
    def __get__(self, instance, owner=None):
        if instance is None:
            return record_get(LOAD(owner), LITERAL("dict"))
        elif instance is SENTINEL:
            # access of `__dict__` on None
            return None
        else:
            return record_get(LOAD(instance), LITERAL("dict"))


def get_cls_slot(cls, name):
    r"""
    Retrieves the dunder method \verb!name! from the provided class \verb!cls!.

    The argument \verb!cls! is required to be a Python type object and
    \verb!name! is required to be a primitive string.
    """
    mro = record_get(LOAD(cls), LITERAL("mro"))
    length = sequence_length(mro)
    index = LITERAL(0)
    while index < length:
        slot = mapping_get_default(
            VALUE_OF(record_get(LOAD(sequence_get(mro, index)), LITERAL("dict"))),
            name,
            None,
        )
        if slot is not None:
            return slot
        index = number_add(index, LITERAL(1))
    return None


def lowlevel_isinstance(obj, cls):
    r"""
    Checks whether \verb!obj! is an instance of \verb!cls!.
    """
    mro = record_get(LOAD(CLS_OF(obj)), LITERAL("mro"))
    length = sequence_length(mro)
    index = LITERAL(0)
    while index < length:
        if sequence_get(mro, index) is cls:
            return True
        index = number_add(index, LITERAL(1))
    return False


def lowlevel_issubclass(cls, other):
    r"""
    Checks whether \verb!cls! is a subclass of \verb!other!.
    """
    if not lowlevel_isinstance(cls, type):
        raise TypeError()
    mro = record_get(LOAD(cls), LITERAL("mro"))
    length = sequence_length(mro)
    index = LITERAL(0)
    while index < length:
        if sequence_get(mro, index) is other:
            return True
        index = number_add(index, LITERAL(1))
    return False


# endregion


# region: Non-Local Variables


def store_global(namespace, identifier, value):
    r"""
    Stores \verb!value! in the provided global namespace.
    """
    namespace[identifier] = value


def load_global(namespace, identifier):
    r"""
    Loads a value from the provided global namespace.
    """
    try:
        return namespace[identifier]
    except KeyError:
        key = VALUE_OF(identifier)
        builtins = LOAD(BUILTINS)
        if mapping_contains(builtins, key):
            return mapping_get(builtins, key)
        else:
            raise NameError()


def load_global_default(namespace, identifier, default):
    r"""
    Loads a value from the provided global namespace. In case no value
    has been bound to \verb!identifier!, the provided default value
    is returned.
    """
    try:
        return load_global(namespace, identifier)
    except NameError:
        return default


def delete_global(namespace, identifier):
    """
    Deletes an identifier from the global namespace.
    """
    try:
        del namespace[identifier]
    except KeyError:
        raise NameError()


def store_class(namespace, identifier, value):
    """
    Stores a value in the namespace of a class.
    """
    namespace[identifier] = value


def load_class_global(class_namespace, global_namespace, identifier):
    """
    Loads a value from the namespace of a class and reverts to the
    provided global namespace in case no value exists in the namespace
    of the class.
    """
    try:
        return class_namespace[identifier]
    except KeyError:
        return load_global(global_namespace, identifier)


def load_class_cell(class_namespace, cells, identifier):
    """
    Loads a value from the namespace of a class and reverts to the
    provided closure in case no value exists in the namespace
    of the class.
    """
    try:
        return class_namespace[identifier]
    except KeyError:
        return load_cell(cells, VALUE_OF(identifier))


# endregion


# region: Attribute Access


def get_attribute(obj, name):
    """
    Retrieves an attribute from an object.
    """
    try:
        return CALL_SLOT(obj, "__getattribute__", name)
    except AttributeError:
        slot = GET_SLOT(obj, "__getattr__")
        if slot is None:
            raise
        return slot(obj, name)


def set_attribute(obj, name, value):
    """
    Sets an attribute on an object.
    """
    slot = GET_SLOT(obj, "__setattr__")
    if slot is None:
        raise ValueError()
    return slot(obj, name, value)


def delete_attribute(obj, name):
    """
    Deletes an attribute from an object.
    """
    CALL_SLOT(obj, "__delattr__", name)


# endregion


# region: Item Access


def set_item(mapping, key, value):
    """
    Sets an item on an object.
    """
    slot = GET_SLOT(mapping, "__setitem__")
    if slot is None:
        raise TypeError()
    slot(mapping, key, value)


def get_item(obj, key):
    """
    Retrieves an item from an object.
    """
    slot = GET_SLOT(obj, "__getitem__")
    if slot is None:
        raise TypeError("object is not subscriptable")
    return slot(obj, key)


def delete_item(mapping, key):
    """
    Deletes an item from an object.
    """
    slot = GET_SLOT(mapping, "__delitem__")
    if slot is None:
        raise TypeError()
    slot(mapping, key)


# endregion


# region: Exception Handling


def ensure_exception(obj_or_cls, context=None):
    r"""
    Constructs an exception from \verb!obj_or_cls!.
    """
    if lowlevel_isinstance(obj_or_cls, BaseException):
        exc = obj_or_cls
    else:
        # TODO: check whether this is a subclass of BaseException
        exc = obj_or_cls()
    # exc.__context__ = context
    # exc.__cause__ = cause
    return exc


def check_active_exception(cls):
    """
    Checks whether there is an active exception.
    """
    if cls is None:
        raise RuntimeError()
    return cls


def is_exception_compatible(exception, pattern):
    """
    Implements the compatibility check specified in Section 8.4. of the PLR.
    """
    return lowlevel_isinstance(exception, pattern)


# endregion


# region: Functions, Methods, and Calling


class BoundMethod:
    def __init__(self, __func__, __self__):
        self.__func__ = __func__
        self.__self__ = __self__

    def __call__(self, *args, **kwargs):
        return self.__func__(self.__self__, *args, **kwargs)

    def __str__(self):
        return "bound method"


class FunctionNameDescriptor:
    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        return NEW_FROM_VALUE(str, record_get(LOAD(instance), LITERAL("name")))

    def __set__(self, instance, value):
        if lowlevel_isinstance(value, str):
            STORE(
                instance, record_set(LOAD(instance), LITERAL("name"), VALUE_OF(value)),
            )
        else:
            raise TypeError()


class FunctionDocDescriptor:
    def __get__(self, instance, owner=None):
        if instance is None:
            return owner.__doc__
        else:
            return record_get(
                LOAD(record_get(LOAD(instance), LITERAL("code"))), LITERAL("doc"),
            )


class function:
    __name__ = FunctionNameDescriptor()
    __doc__ = FunctionDocDescriptor()

    def __new__(cls, *args, **kwargs):
        # functions cannot be instantiated, see `build_function`
        raise TypeError()

    def __str__(self):
        return "function"

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        elif instance is SENTINEL:
            return BoundMethod(self, None)
        else:
            return BoundMethod(self, instance)

    def __call__(self, *args, **kwargs):
        # this does not invoke `__call__` again because `self` is a function
        return self(*args, **kwargs)


def bind(signature, defaults, positional_arguments, keyword_arguments):
    index = LITERAL(0)
    namespace = LITERAL({})
    length = sequence_length(signature)
    last_positional = LITERAL(-1)
    positional_max = number_sub(sequence_length(positional_arguments), LITERAL(1))
    while index < length:
        parameter = sequence_get(signature, index)
        name = record_get(parameter, LITERAL("name"))
        kind = record_get(parameter, LITERAL("kind"))
        if kind == LITERAL("POSITIONAL_OR_KEYWORD"):
            if index < sequence_length(positional_arguments):
                argument = sequence_get(positional_arguments, index)
                last_positional = index
            elif mapping_contains(keyword_arguments, name):
                argument = mapping_get(keyword_arguments, name)
                keyword_arguments = mapping_delete(keyword_arguments, name)
            elif mapping_contains(defaults, name):
                argument = mapping_get(defaults, name)
            else:
                raise TypeError("argument missing")
        elif kind == LITERAL("VARIABLE_POSITIONAL"):
            argument = NEW_FROM_VALUE(
                tuple,
                sequence_slice(
                    positional_arguments, index, sequence_length(positional_arguments),
                ),
            )
            last_positional = positional_max
        elif kind == LITERAL("KEYWORD_ONLY"):
            if mapping_contains(keyword_arguments, name):
                argument = mapping_get(keyword_arguments, name)
                keyword_arguments = mapping_delete(keyword_arguments, name)
            elif mapping_contains(defaults, name):
                argument = mapping_get(defaults, name)
            else:
                raise TypeError("argument missing")
        else:
            assert kind == LITERAL("VARIABLE_KEYWORD")
            mapping = {}
            keys = mapping_keys(keyword_arguments)
            index = LITERAL(0)
            length = sequence_length(keys)
            while index < length:
                key = sequence_get(keys, index)
                if mapping_contains(namespace, key):
                    raise TypeError("duplicate argument")
                mapping[NEW_FROM_VALUE(str, key)] = mapping_get(keyword_arguments, key)
                index = number_add(index, LITERAL(1))
            argument = mapping
            keyword_arguments = LITERAL({})
        namespace = mapping_set(namespace, name, argument)
        index = number_add(index, LITERAL(1))
    if mapping_size(keyword_arguments) != LITERAL(0):
        raise TypeError("unexpected keyword arguments")
    elif last_positional != positional_max:
        raise TypeError("too many positional arguments")
    return namespace


class GeneratorRunningDescriptor:
    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        else:
            return record_get_default(LOAD(instance), LITERAL("is_running"), False)


class generator:
    gi_running = GeneratorRunningDescriptor()

    def __iter__(self):
        return self

    def __next__(self):
        return self.send(None)

    def send(self, value):
        frame = VALUE_OF(self)
        if frame is None:
            raise StopIteration()
        try:
            STORE(self, record_set(LOAD(self), LITERAL("is_running"), True))
            result = send_value(frame, value)
        except:
            SET_VALUE(self, None)
            raise
        finally:
            STORE(self, record_set(LOAD(self), LITERAL("is_running"), False))
        SET_VALUE(self, record_get(result, LITERAL("frame")))
        if record_get(result, LITERAL("frame")) is None:
            value = record_get(result, LITERAL("value"))
            if value is None:
                raise StopIteration()
            else:
                raise StopIteration(value)
        return record_get(result, LITERAL("value"))

    def throw(self, exc_typ, exc_val=None, exc_tb=None):
        # TODO: `exc_val` and `exc_tb` are ignored
        exc_val = exc_val or exc_typ()
        frame = VALUE_OF(self)
        if frame is None:
            raise StopIteration()
        try:
            STORE(self, record_set(LOAD(self), LITERAL("is_running"), True))
            result = send_throw(frame, exc_val)
        except:
            SET_VALUE(self, None)
            raise
        finally:
            STORE(self, record_set(LOAD(self), LITERAL("is_running"), False))
        SET_VALUE(self, record_get(result, LITERAL("frame")))
        if record_get(result, LITERAL("frame")) is None:
            value = record_get(result, LITERAL("value"))
            if value is None:
                raise StopIteration()
            else:
                raise StopIteration(value)
        return record_get(result, LITERAL("value"))

    def close(self):
        try:
            self.throw(GeneratorExit)
            raise RuntimeError("generator returned a value when closed")
        except GeneratorExit:
            pass
        except StopIteration:
            pass


def call(positional_arguments, keyword_arguments, target):
    """
    Calls a callable object with the provided arguments.
    """
    cls = CLS_OF(target)
    if cls is function:
        descriptor = LOAD(target)
        code = LOAD(record_get(descriptor, LITERAL("code")))
        signature = record_get(code, LITERAL("signature"))
        defaults = record_get(descriptor, LITERAL("defaults"))
        namespace = bind(signature, defaults, positional_arguments, keyword_arguments)
        cells = record_get(descriptor, LITERAL("cells"))

        length = sequence_length(record_get(code, LITERAL("cells")))
        if length != LITERAL(0):
            own_cells = record_get(code, LITERAL("cells"))
            index = LITERAL(0)
            while index < length:
                cell_name = sequence_get(own_cells, index)
                cell = Cell()
                if mapping_contains(namespace, cell_name):
                    cell.set_value(mapping_get(namespace, cell_name))
                cells = mapping_set(cells, cell_name, cell)
                index = number_add(index, LITERAL(1))

        namespace = mapping_set(
            mapping_set(
                namespace,
                LITERAL("__globals__"),
                record_get(descriptor, LITERAL("globals")),
            ),
            LITERAL("__cells__"),
            cells,
        )
        frame = make_frame(code, namespace)
        if record_get(code, LITERAL("is_generator")):
            return NEW_FROM_VALUE(generator, frame)
        return CALL(frame)
    else:
        slot = GET_SLOT(target, "__call__")
        if slot is None:
            raise TypeError("object is not callable")
        else:
            return call(
                sequence_push_left(positional_arguments, target),
                keyword_arguments,
                slot,
            )


def build_function(code, global_namespace, cells, defaults):
    """
    Constructs a function object from the provided code, global namespace,
    closure, and default values for parameters.
    """
    code_descriptor = LOAD(code)
    cell_identifiers = record_get(code_descriptor, LITERAL("cells"))
    index = LITERAL(0)
    length = sequence_length(cell_identifiers)
    while index < length:
        cells = mapping_set(cells, sequence_get(cell_identifiers, index), Cell())
        index = number_add(index, LITERAL(1))
    module = None
    try:
        module = global_namespace["__name__"]
    except KeyError:
        pass
    attrs = mapping_set(
        mapping_set(
            LITERAL({}),
            LITERAL("__doc__"),
            record_get(code_descriptor, LITERAL("doc")),
        ),
        LITERAL("__module__"),
        module,
    )
    return NEW(
        RECORD(
            cls=function,
            code=code,
            name=record_get(code_descriptor, LITERAL("name")),
            globals=global_namespace,
            cells=cells,
            defaults=defaults,
            dict=NEW_FROM_VALUE(mappingproxy, attrs),
        )
    )


# endregion


# region: Comparision Operations

# https://github.com/python/cpython/blob/3094dd5fb5fa3ed91f5e2887887b193edbc976d2/Objects/object.c#L657


def cmp_in(obj, container):
    return CALL_SLOT(container, "__contains__", obj)


def cmp_not_in(obj, container):
    return not CALL_SLOT(container, "__contains__", obj)


def rich_cmp(left, right, normal, swapped):
    """
    Implements rich comparisons between two objects.
    """

    # this is how CPython implements it despite it being specified differently
    left_cls = CLS_OF(left)
    right_cls = CLS_OF(right)

    if left_cls is not right_cls and lowlevel_issubclass(right_cls, left_cls):
        # let's swap everything
        tmp = left_cls
        left_cls = right_cls
        right_cls = tmp
        tmp = left
        left = right
        right = tmp
        tmp = normal
        normal = swapped
        swapped = tmp

    result = NotImplemented

    slot = get_cls_slot(left_cls, normal)
    if slot is not None:
        result = slot(left, right)

    if result is NotImplemented:
        slot = get_cls_slot(right_cls, swapped)
        if slot is not None:
            result = slot(right, left)

    if result is NotImplemented:
        if normal is LITERAL("__eq__"):
            return left is right
        elif normal is LITERAL("__ne__"):
            return left is not right
        raise TypeError()

    return result


def cmp_eq(left, right):
    return rich_cmp(left, right, LITERAL("__eq__"), LITERAL("__eq__"))


def cmp_ne(left, right):
    return rich_cmp(left, right, LITERAL("__ne__"), LITERAL("__ne__"))


def cmp_lt(left, right):
    return rich_cmp(left, right, LITERAL("__lt__"), LITERAL("__gt__"))


def cmp_le(left, right):
    return rich_cmp(left, right, LITERAL("__le__"), LITERAL("__ge__"))


def cmp_ge(left, right):
    return rich_cmp(left, right, LITERAL("__ge__"), LITERAL("__le__"))


def cmp_gt(left, right):
    return rich_cmp(left, right, LITERAL("__gt__"), LITERAL("__lt__"))


# endregion


# region: Binary and Unary Operators


def binary_operator(left, right, left_slot, right_slot):
    r"""
    Applies a binary operator to the provided operands.
    """

    result = NotImplemented

    slot = get_cls_slot(CLS_OF(left), left_slot)
    if slot is not None:
        result = slot(left, right)

    if result is NotImplemented:
        slot = get_cls_slot(CLS_OF(right), right_slot)
        if slot is not None:
            result = slot(right, left)

    if result is NotImplemented:
        raise ValueError()
    else:
        return result


def unary_operator(operand, slot_name):
    """
    Applies a unary operator to the provided operand.
    """
    slot = get_cls_slot(CLS_OF(operand), slot_name)
    if slot is None:
        raise TypeError()
    else:
        return slot(operand)


# endregion


# region: Unpacking


def unpack_iterable(iterable):
    """
    Takes an iterable and returns a primitive vector of its elemens.
    """
    if CLS_OF(iterable) is tuple:
        return VALUE_OF(iterable)
    else:
        elements = LITERAL(())
        for element in iterable:
            elements = sequence_push(elements, element)
        return elements


def unpack_str_mapping(mapping):
    """
    Takes a python mapping and returns a primitive mapping.
    """
    entries = record_get_default(LOAD(mapping), LITERAL("value"), None)
    # shortcircuit if `mapping` is an empty dictionary
    if entries is not None and sequence_length(entries) == LITERAL(0):
        return LITERAL({})
    result = LITERAL({})
    for key in mapping:
        if lowlevel_isinstance(key, str):
            result = mapping_set(result, VALUE_OF(key), mapping[key])
        else:
            raise TypeError()
    return result


# endregion


# region: NoneType


class NoneType:
    def __new__(cls):
        return None

    def __str__(self):
        return "None"

    def __bool__(self):
        return False

    def __getattribute__(self, name):
        # XXX: Descriptors on `NoneType` are only builtin descriptors
        # which will understand the use of SENTINEL as an instance in
        # place of `None`. This hack is necessary because passing `None`
        # as the instance means no-instance access, i.e., accessing a
        # class attribute on the owner.
        if not lowlevel_isinstance(name, str):
            raise TypeError()
        value = getattribute_type(NoneType, name, SENTINEL)
        if value is SENTINEL:
            raise AttributeError()
        else:
            return value


# endregion


# region: Type Auxillary Descriptors and Functions


class TypeMRODescriptor:
    def __get__(self, instance, owner=None):
        if instance is None:
            return NEW_FROM_VALUE(tuple, record_get(LOAD(owner), LITERAL("mro")))
        else:
            return NEW_FROM_VALUE(tuple, record_get(LOAD(instance), LITERAL("mro")))


class TypeNameDescriptor:
    def __get__(self, instance, owner=None):
        if instance is None:
            return NEW_FROM_VALUE(str, record_get(LOAD(owner), LITERAL("name")))
        else:
            return NEW_FROM_VALUE(str, record_get(LOAD(instance), LITERAL("name")))


class TypeBasesDescriptor:
    def __get__(self, instance, owner=None):
        if instance is None:
            return NEW_FROM_VALUE(tuple, record_get(LOAD(owner), LITERAL("bases")))
        else:
            return NEW_FROM_VALUE(tuple, record_get(LOAD(instance), LITERAL("bases")))


def getattribute_type(cls, name, instance):
    mro = record_get(LOAD(cls), LITERAL("mro"))
    index = LITERAL(0)
    length = sequence_length(mro)
    while index < length:
        mro_cls = sequence_get(mro, index)
        attrs = record_get(LOAD(mro_cls), LITERAL("dict"))
        if attrs is not None:
            try:
                value = attrs[name]
            except KeyError:
                pass
            else:
                descriptor_get = GET_SLOT(value, "__get__")
                if descriptor_get is None:
                    return value
                else:
                    return descriptor_get(value, instance, cls)
        index = number_add(index, LITERAL(1))
    return SENTINEL


def cls_get__get__descriptor(cls, name):
    mro = record_get(LOAD(cls), LITERAL("mro"))
    index = LITERAL(0)
    length = sequence_length(mro)
    name_value = VALUE_OF(name)
    while index < length:
        mro_cls = sequence_get(mro, index)
        attrs = record_get(LOAD(mro_cls), LITERAL("dict"))
        # should be true for all types/classes
        if lowlevel_isinstance(attrs, mappingproxy):
            mapping = VALUE_OF(attrs)
            if mapping_contains(mapping, name_value):
                value = mapping_get(mapping, name_value)
                if GET_SLOT(value, "__get__") is None:
                    return value
        index = number_add(index, LITERAL(1))
    return SENTINEL


def cls_get__set__descriptor(cls, name):
    mro = record_get(LOAD(cls), LITERAL("mro"))
    index = LITERAL(0)
    length = sequence_length(mro)
    name_value = VALUE_OF(name)
    while index < length:
        mro_cls = sequence_get(mro, index)
        attrs = record_get(LOAD(mro_cls), LITERAL("dict"))
        # should be true for all types/classes
        if lowlevel_isinstance(attrs, mappingproxy):
            mapping = VALUE_OF(attrs)
            if mapping_contains(mapping, name_value):
                value = mapping_get(mapping, name_value)
                # The following item-access would lead to an infinite recurision:
                #   value = attrs[name]
                # If the attribute is not found, a KeyError is constructed on which
                # the attribute `args` is set. Leading to an infinite recurision. Hence,
                # we directly access the mappingproxy here.
                if GET_SLOT(value, "__set__") is None:
                    return SENTINEL
                else:
                    return value
        index = number_add(index, LITERAL(1))
    return SENTINEL


def cls_get__delete__descriptor(cls, name):
    mro = record_get(LOAD(cls), LITERAL("mro"))
    index = LITERAL(0)
    length = sequence_length(mro)
    name_value = VALUE_OF(name)
    while index < length:
        mro_cls = sequence_get(mro, index)
        attrs = record_get(LOAD(mro_cls), LITERAL("dict"))
        # should be true for all types/classes
        if lowlevel_isinstance(attrs, mappingproxy):
            mapping = VALUE_OF(attrs)
            if mapping_contains(mapping, name_value):
                value = mapping_get(mapping, name_value)
                if GET_SLOT(value, "__delete__") is None:
                    return SENTINEL
                else:
                    return value
        index = number_add(index, LITERAL(1))
    return SENTINEL


def compute_cls_layout(mro):
    """
    Computes the class layout based on the MRO.
    """
    length = sequence_length(mro)
    index = LITERAL(0)
    layout = object
    while index < length:
        mro_cls = sequence_get(mro, index)
        cls_layout = record_get_default(LOAD(mro_cls), LITERAL("layout"), object)
        if cls_layout is not object:
            if layout is object:
                layout = cls_layout
            elif layout is not cls_layout:
                # Invalid combination of layouts.
                raise TypeError()
        index = number_add(index, LITERAL(1))
    return layout


def compute_mro(cls, bases):
    r"""
    Computes the method resolution order (MRO) for \verb!cls!.
    """
    result = LITERAL((cls,))
    pending = LITERAL(())

    length = sequence_length(bases)
    index = LITERAL(0)
    while index < length:
        base = sequence_get(bases, index)
        # check for duplicate base classes
        other_index = number_add(index, LITERAL(1))
        while other_index < length:
            if base is sequence_get(bases, other_index):
                raise TypeError()
            other_index = number_add(other_index, LITERAL(1))

        if record_get_default(LOAD(base), LITERAL("is_sealed"), False):
            # cannot be subclassed
            raise TypeError()
        mro = record_get_default(LOAD(base), LITERAL("mro"), None)
        if mro is None:
            raise TypeError()
        pending = sequence_push(pending, mro)
        index = number_add(index, LITERAL(1))

    pending = sequence_push(pending, bases)

    remaining = sequence_length(pending)
    while remaining != LITERAL(0):
        index = LITERAL(0)
        while index < remaining:
            mro = sequence_get(pending, index)
            head = sequence_get(mro, LITERAL(0))

            good = True

            # let's determine whether the `head` is “good”
            other_index = LITERAL(0)
            while other_index < remaining and good:
                if other_index != index:
                    other_mro = sequence_get(pending, other_index)
                    other_mro_index = LITERAL(1)
                    other_mro_length = sequence_length(other_mro)
                    while other_mro_index < other_mro_length:
                        other_cls = sequence_get(other_mro, other_mro_index)
                        if other_cls == head:
                            good = False
                            break
                        other_mro_index = number_add(other_mro_index, LITERAL(1))
                other_index = number_add(other_index, LITERAL(1))

            if good:
                result = sequence_push(result, head)

                still_pending = LITERAL(())
                other_index = LITERAL(0)
                while other_index < remaining:
                    other_mro = sequence_get(pending, other_index)
                    other_head = sequence_get(other_mro, LITERAL(0))
                    if other_head == head:
                        other_mro = sequence_pop_left(other_mro)
                    if sequence_length(other_mro) != LITERAL(0):
                        still_pending = sequence_push(still_pending, other_mro)
                    other_index = number_add(other_index, LITERAL(1))

                pending = still_pending
                remaining = sequence_length(pending)

                break

            index = number_add(index, LITERAL(1))
        else:
            raise TypeError("unable to linearize class hierarchy")
    return result


def extract_metaclass(bases):
    mcs = type
    length = sequence_length(bases)
    index = LITERAL(0)
    while index < length:
        base_mcs = CLS_OF(sequence_get(bases, index))
        if lowlevel_issubclass(base_mcs, mcs):
            mcs = base_mcs
        elif not lowlevel_issubclass(mcs, base_mcs):
            raise TypeError("inconsistent metaclasses")
        index = number_add(index, LITERAL(1))
    return mcs


# endregion


# region: Other Auxillary Functions


def create_assertion_error(message):
    r"""
    Creates an \verb!AssertionError!.
    """
    return AssertionError(message)


def unbound_local_error(identifier):
    r"""
    Creates an \verb!UnboundLocalError!.
    """
    raise UnboundLocalError(identifier)


def convert_bool(obj):
    """
    Converts an object to a boolean.
    """
    slot = GET_SLOT(obj, "__bool__")
    if slot is None:
        raise ValueError()
    return slot(obj)


def runtime_iter(obj):
    # TODO: call `__iter__` or use the sequence protocol
    return CALL_SLOT(obj, "__iter__")


def raise_primitive_error(message):
    raise SystemError(NEW_FROM_VALUE(str, message))


def print_exception(exc):
    try:
        message = exc.args[0]
    except IndexError:
        message = ""
    print(exc.__class__.__name__, ": ", message, sep="")


# endregion
