# -*- coding: utf-8 -*-
#
# Copyright (C) 2020, Maximilian Köhl <mail@koehlma.de>
#
# type: ignore
# flake8: noqa

"""
Definition of Python's builtins using the semantic primitives.
"""

from .prelude import *
from .runtime import *


raise AssertionError("this file should never be imported")


# region: Builtin Datatypes


class object:
    __class__ = ClassDescriptor()
    __dict__ = DictDescriptor()

    def __new__(cls, *args, **kwargs):
        if record_get(LOAD(cls), LITERAL("layout")) is not object:
            raise TypeError("invalid layout for object.__new__")
        elif cls is object:
            return NEW(RECORD(cls=cls, dict=None))
        else:
            return NEW(RECORD(cls=cls, dict=NEW_FROM_VALUE(dict, LITERAL(()))))

    def __init__(self, *args, **kwargs):
        pass

    def __repr__(self):
        return NEW_FROM_VALUE(
            str,
            string_join(
                LITERAL(" "),
                LITERAL(
                    (
                        LITERAL("<object at"),
                        number_str(reference_id(self)),
                        LITERAL(">"),
                    )
                ),
            ),
        )

    def __str__(self):
        return repr(self)

    def __bool__(self):
        return True

    def __hash__(self):
        return NEW_FROM_VALUE(int, reference_hash(self))

    def __getattribute__(self, name):
        if not lowlevel_isinstance(name, str):
            raise TypeError()
        descriptor = cls_get__set__descriptor(CLS_OF(self), name)
        if descriptor is SENTINEL:
            attrs = record_get(LOAD(self), LITERAL("dict"))
            if attrs is not None:
                try:
                    return attrs[name]
                except KeyError:
                    pass
            value = getattribute_type(CLS_OF(self), name, self)
            if value is SENTINEL:
                raise AttributeError()
            else:
                return value
        else:
            return CALL_SLOT(descriptor, "__get__", self, CLS_OF(self))

    def __setattr__(self, name, value):
        if not lowlevel_isinstance(name, str):
            raise TypeError()
        if lowlevel_isinstance(self, type):
            raise TypeError()
        descriptor = cls_get__set__descriptor(CLS_OF(self), name)
        if descriptor is SENTINEL:
            attrs = record_get(LOAD(self), LITERAL("dict"))
            if attrs is None:
                raise AttributeError()
            attrs[name] = value
        else:
            CALL_SLOT(descriptor, "__set__", self, value)

    def __delattr__(self, name):
        if not lowlevel_isinstance(name, str):
            raise TypeError()
        if lowlevel_isinstance(self, type):
            raise TypeError()
        descriptor = cls_get__delete__descriptor(CLS_OF(self), name)
        if descriptor is SENTINEL:
            attrs = record_get(LOAD(self), LITERAL("dict"))
            if attrs is None:
                raise AttributeError()
            try:
                del attrs[name]
            except KeyError:
                raise AttributeError()
        else:
            CALL_SLOT(descriptor, "__delete__", self)

    def __eq__(self, other):
        return True if self is other else NotImplemented

    def __ne__(self, other):
        result = CALL_SLOT(self, "__eq__", other)
        if result is not NotImplemented:
            result = not result
        return result

    def __lt__(self, other):
        return NotImplemented

    def __le__(self, other):
        return NotImplemented

    def __ge__(self, other):
        return NotImplemented

    def __gt__(self, other):
        return NotImplemented


class type:
    __name__ = TypeNameDescriptor()
    __mro__ = TypeMRODescriptor()
    __bases__ = TypeBasesDescriptor()

    def __new__(self, name_or_obj=None, bases=None, namespace=None, **kwargs):
        if bases is None and namespace is None:
            return CLS_OF(name_or_obj)
        if not lowlevel_isinstance(name_or_obj, str):
            raise TypeError()
        name = name_or_obj

        # transfer the namespace into a primitive mapping
        attrs = LITERAL({})
        for key in namespace:
            attrs = mapping_set(attrs, VALUE_OF(key), namespace[key])
        # set `__hash__` to `None` if `__eq__` is defined but `__hash__` is undefined
        if mapping_contains(attrs, LITERAL("__eq__")) and not mapping_contains(
            attrs, LITERAL("__hash__")
        ):
            attrs = mapping_set(attrs, LITERAL("__hash__"), None)

        # unpack the bases into a sequence and add `object` if there are no bases
        bases = unpack_iterable(bases)
        if sequence_length(bases) == LITERAL(0):
            bases = sequence_push(bases, object)

        # create the instance of the meta class
        instance = NEW(
            RECORD(
                cls=self,
                dict=NEW_FROM_VALUE(mappingproxy, attrs),
                name=VALUE_OF(name),
                bases=bases,
            )
        )

        # update the MRO and the layout of the type
        mro = compute_mro(instance, bases)
        layout = compute_cls_layout(mro)
        STORE(
            instance,
            record_set(
                record_set(LOAD(instance), LITERAL("mro"), mro),
                LITERAL("layout"),
                layout,
            ),
        )

        return instance

    def __init__(self, name, bases, namespace, **kwargs):
        pass

    def __prepare__(name, bases, **kwargs):
        return {}

    def __getattribute__(self, name):
        if not lowlevel_isinstance(name, str):
            raise TypeError()
        value = getattribute_type(self, name, None)
        if value is SENTINEL:
            value = getattribute_type(CLS_OF(self), name, self)
            if value is SENTINEL:
                raise AttributeError()
        return value

    def __setattr__(self, name, value):
        if not lowlevel_isinstance(name, str) or not lowlevel_isinstance(self, type):
            raise TypeError()
        if record_get_default(LOAD(self), LITERAL("is_builtin"), False):
            raise TypeError("cannot set attribute on built-in type")
        descriptor = cls_get__set__descriptor(CLS_OF(self), name)
        if descriptor is SENTINEL:
            self_dict = record_get(LOAD(self), LITERAL("dict"))
            if self_dict is None:
                raise AttributeError()
            self_dict[name] = value
        else:
            CALL_SLOT(descriptor, "__set__", self, value)

    def __repr__(self):
        return NEW_FROM_VALUE(
            str,
            string_join(
                LITERAL(" "),
                LITERAL(
                    (
                        LITERAL("<type '"),
                        record_get(LOAD(self), LITERAL("name")),
                        LITERAL("'>"),
                    )
                ),
            ),
        )

    def __instancecheck__(self, instance):
        return lowlevel_isinstance(instance, self)

    def __subclasscheck__(self, subclass):
        return lowlevel_issubclass(subclass, self)

    def __call__(self, *args, **kwargs):
        instance = GET_CLS_SLOT(self, "__new__")(self, *args, **kwargs)
        if GET_SLOT(instance, "__init__")(instance, *args, **kwargs) is not None:
            raise TypeError()
        return instance


class str:
    def __new__(cls, value=SENTINEL):
        if value is SENTINEL:
            value = LITERAL("")
        else:
            value = VALUE_OF(CALL_SLOT(value, "__str__"))
        if cls is str:
            return NEW_FROM_VALUE(str, value)
        else:
            return NEW(
                RECORD(cls=cls, dict=NEW_FROM_VALUE(dict, LITERAL(())), value=value)
            )

    def __init__(self, value=None):
        pass

    def __len__(self):
        return NEW_FROM_VALUE(int, string_length(VALUE_OF(self)))

    def __hash__(self):
        return NEW_FROM_VALUE(int, string_hash(VALUE_OF(self)))

    def __repr__(self):
        return NEW_FROM_VALUE(str, string_repr(VALUE_OF(self)))

    def __bool__(self):
        if string_length(VALUE_OF(self)) == LITERAL(0):
            return False
        return True

    def __str__(self):
        if CLS_OF(self) is str:
            return self
        else:
            return NEW_FROM_VALUE(str, VALUE_OF(self))

    def __eq__(self, other):
        if CLS_OF(other) is not CLS_OF(self):
            return False
        if string_equals(VALUE_OF(self), VALUE_OF(other)):
            return True
        else:
            return False

    def __add__(self, other):
        if lowlevel_isinstance(other, str):
            return NEW_FROM_VALUE(str, string_concat(VALUE_OF(self), VALUE_OF(other)))
        else:
            raise TypeError()

    def join(self, iterable):
        raise NotImplementedError()

    def rpartition(self, seperator):
        if lowlevel_isinstance(seperator, str):
            partition = string_rpartition(VALUE_OF(self), VALUE_OF(seperator))
            return NEW_FROM_VALUE(
                tuple,
                LITERAL(
                    (
                        NEW_FROM_VALUE(str, sequence_get(partition, LITERAL(0))),
                        NEW_FROM_VALUE(str, sequence_get(partition, LITERAL(1))),
                        NEW_FROM_VALUE(str, sequence_get(partition, LITERAL(2))),
                    )
                ),
            )

        else:
            raise TypeError()


class int:
    def __new__(cls, value=SENTINEL):
        if value is SENTINEL:
            return 0
        if not lowlevel_issubclass(cls, int):
            raise TypeError()
        value = VALUE_OF(CALL_SLOT(value, "__int__"))
        if cls is int:
            return NEW_FROM_VALUE(int, value)
        else:
            return NEW(
                RECORD(cls=cls, dict=NEW_FROM_VALUE(dict, LITERAL(())), value=value)
            )

    def __repr__(self):
        return NEW_FROM_VALUE(str, number_str(VALUE_OF(self)))

    def __int__(self):
        return NEW_FROM_VALUE(int, VALUE_OF(self))

    def __index__(self):
        return self

    def __bool__(self):
        if VALUE_OF(self) != LITERAL(0):
            return True
        return False

    def __hash__(self):
        return NEW_FROM_VALUE(int, number_hash(VALUE_OF(self)))

    def __eq__(self, other):
        if lowlevel_isinstance(other, int):
            if VALUE_OF(self) == VALUE_OF(other):
                return True
            return False
        else:
            return NotImplemented

    def __ne__(self, other):
        if lowlevel_isinstance(other, int):
            if VALUE_OF(self) != VALUE_OF(other):
                return True
            return False
        else:
            return NotImplemented

    def __lt__(self, other):
        if VALUE_OF(self) < VALUE_OF(other):
            return True
        return False

    def __le__(self, other):
        if VALUE_OF(self) <= VALUE_OF(other):
            return True
        return False

    def __ge__(self, other):
        if VALUE_OF(self) >= VALUE_OF(other):
            return True
        return False

    def __gt__(self, other):
        if VALUE_OF(self) > VALUE_OF(other):
            return True
        return False

    def __add__(self, other):
        if lowlevel_isinstance(other, int):
            return NEW_FROM_VALUE(int, number_add(VALUE_OF(self), VALUE_OF(other)))
        return NotImplemented

    def __sub__(self, other):
        if lowlevel_isinstance(other, int):
            return NEW_FROM_VALUE(int, number_sub(VALUE_OF(self), VALUE_OF(other)))
        return NotImplemented

    def __mul__(self, other):
        if lowlevel_isinstance(other, int):
            return NEW_FROM_VALUE(int, number_mul(VALUE_OF(self), VALUE_OF(other)))
        return NotImplemented


class bool(int):
    def __new__(cls, obj=False):
        if obj:
            return True
        else:
            return False

    def __init__(self, obj=False):
        pass

    def __bool__(self):
        return self

    def __repr__(self):
        if self:
            return "True"
        else:
            return "False"


class dict:
    def __new__(cls, *args, **kwargs):
        if cls is dict:
            return NEW_FROM_VALUE(dict, LITERAL(()))
        else:
            return NEW(
                RECORD(
                    cls=cls, dict=NEW_FROM_VALUE(dict, LITERAL(())), value=LITERAL(()),
                )
            )

    def __init__(self, *args, **kwargs):
        if len(args) == 0:
            for key in kwargs:
                self[key] = kwargs[key]
        elif len(args) == 1 and len(kwargs) == 0:
            initializer = args[0]
            try:
                initializer = initializer.items()
            except AttributeError:
                pass
            for item in initializer:
                iterator = iter(item)
                key = next(iterator)
                value = next(iterator)
                try:
                    next(iterator)
                except StopIteration:
                    pass
                else:
                    raise ValueError()
                self[key] = value
        else:
            raise ValueError()

    def __eq__(self, other):
        if lowlevel_isinstance(other, dict):
            self_entries = VALUE_OF(self)
            other_entries = VALUE_OF(other)
            length = sequence_length(self_entries)
            if length != sequence_length(other_entries):
                return False
            index = LITERAL(0)
            while index < length:
                entry = sequence_get(self_entries, index)
                key = record_get(entry, LITERAL("key"))
                value = record_get(entry, LITERAL("value"))
                other_index = LITERAL(0)
                while other_index < length:
                    other_entry = sequence_get(other_entries, other_index)
                    other_key = record_get(other_entry, LITERAL("key"))
                    other_value = record_get(other_entry, LITERAL("value"))
                    if key == other_key:
                        if value == other_value:
                            break
                        else:
                            return False
                    other_index = number_add(other_index, LITERAL(1))
                else:
                    return False
                index = number_add(index, LITERAL(1))
            return True
        else:
            return NotImplemented

    def __iter__(self):
        return NEW_FROM_VALUE(
            DictKeyIterator, RECORD(index=LITERAL(0), entries=VALUE_OF(self)),
        )

    def __contains__(self, key):
        return dict_find_entry(self, key, VALUE_OF(hash(key))) is not None

    def __len__(self):
        return NEW_FROM_VALUE(int, sequence_length(VALUE_OF(self)))

    def __bool__(self):
        if sequence_length(VALUE_OF(self)) == LITERAL(0):
            return False
        return True

    def __getitem__(self, key):
        index = dict_find_entry(self, key, VALUE_OF(hash(key)))
        if index is None:
            raise KeyError()
        return record_get(sequence_get(VALUE_OF(self), index), LITERAL("value"))

    def __setitem__(self, key, value):
        key_hash = VALUE_OF(hash(key))
        index = dict_find_entry(self, key, key_hash)
        entries = VALUE_OF(self)
        if index is not None:
            entries = sequence_delete(entries, index)
        SET_VALUE(
            self, sequence_push(entries, RECORD(key=key, value=value, hash=key_hash)),
        )

    def __delitem__(self, key):
        index = dict_find_entry(self, key, VALUE_OF(hash(key)))
        if index is None:
            raise KeyError()
        SET_VALUE(self, sequence_delete(VALUE_OF(self), index))

    def items(self):
        return MappingItemsIterator(self)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default


class tuple:
    def __new__(cls, iterable=SENTINEL):
        if iterable is SENTINEL:
            return NEW_FROM_VALUE(cls, LITERAL(()))
        else:
            if cls is tuple and CLS_OF(iterable) is tuple:
                return iterable
            return NEW_FROM_VALUE(cls, unpack_iterable(iterable))

    def __init__(self, iterable=SENTINEL):
        pass

    def __contains__(self, obj):
        for element in self:
            if element == obj:
                return True
        return False

    def __repr__(self):
        elements = LITERAL(())
        for element in self:
            elements = sequence_push(elements, VALUE_OF(repr(element)))
        return NEW_FROM_VALUE(
            str,
            string_join(
                LITERAL(" "),
                (
                    LITERAL(
                        (
                            LITERAL("("),
                            string_join(LITERAL(", "), elements),
                            LITERAL(")"),
                        )
                    )
                ),
            ),
        )

    def __eq__(self, other):
        if not lowlevel_isinstance(other, tuple):
            return NotImplemented
        return runtime_sequence_equals(VALUE_OF(self), VALUE_OF(other))

    def __hash__(self):
        # https://github.com/python/cpython/blob/3.7/Objects/tupleobject.c#L348
        # Taken from `Include/pyhash.h`.
        mult = 1000003
        x = 0x345678
        length = len(self)

        for item in self:
            y = hash(item)
            if y == -1:
                return -1
            x = (x ^ y) * mult
            mult = (mult + (82520 + length + length)) & 0xFFFF_FFFF_FFFF_FFFF

        x = x + 97531
        return x

    def __len__(self):
        return NEW_FROM_VALUE(int, sequence_length(VALUE_OF(self)))

    def __getitem__(self, index):
        return runtime_sequence_get(
            VALUE_OF(self), VALUE_OF(CALL_SLOT(index, "__index__"))
        )

    def __iter__(self):
        return NEW_FROM_VALUE(
            tuple_iterator, RECORD(sequence=VALUE_OF(self), index=LITERAL(0))
        )

    def __bool__(self):
        if sequence_length(VALUE_OF(self)) == LITERAL(0):
            return False
        return True

    def __add__(self, other):
        if lowlevel_isinstance(other, tuple):
            self_value = VALUE_OF(self)
            other_value = VALUE_OF(other)
            return NEW_FROM_VALUE(tuple, sequence_concat(self_value, other_value))
        else:
            return NotImplemented


class list:
    def __new__(cls, iterable=SENTINEL):
        return NEW_FROM_VALUE(cls, LITERAL(()))

    def __init__(self, iterable=SENTINEL):
        if iterable is not SENTINEL:
            SET_VALUE(self, unpack_iterable(iterable))

    def __add__(self, other):
        if lowlevel_isinstance(other, list):
            self_value = VALUE_OF(self)
            other_value = VALUE_OF(other)
            return NEW_FROM_VALUE(list, sequence_concat(self_value, other_value))
        else:
            return NotImplemented

    def __iter__(self):
        return list_iterator(self)

    def __getitem__(self, index):
        return runtime_sequence_get(
            VALUE_OF(self), VALUE_OF(CALL_SLOT(index, "__index__"))
        )

    def __setitem__(self, index, value):
        SET_VALUE(self, runtime_sequence_set(VALUE_OF(self), VALUE_OF(index), value))

    def __len__(self):
        return NEW_FROM_VALUE(int, sequence_length(VALUE_OF(self)))

    def __bool__(self):
        if sequence_length(VALUE_OF(self)) == LITERAL(0):
            return False
        return True

    def __eq__(self, other):
        if not lowlevel_isinstance(other, list):
            return NotImplemented
        return runtime_sequence_equals(VALUE_OF(self), VALUE_OF(other))

    def append(self, element):
        SET_VALUE(self, sequence_push(VALUE_OF(self), element))

    def extend(self, iterable):
        SET_VALUE(self, sequence_concat(VALUE_OF(self), unpack_iterable(iterable)))


# endregion


# region: Exceptions


class BaseException:
    def __init__(self, *args):
        self.args = args


class SystemExit(BaseException):
    pass


class KeyboardInterrupt(BaseException):
    pass


class GeneratorExit(BaseException):
    pass


class Exception(BaseException):
    pass


class StopIteration(Exception):
    pass


class StopAsyncIteration(Exception):
    pass


class ArithmeticError(Exception):
    pass


class FloatingPointError(ArithmeticError):
    pass


class OverflowError(ArithmeticError):
    pass


class ZeroDivisionError(ArithmeticError):
    pass


class AssertionError(Exception):
    pass


class AttributeError(Exception):
    pass


class BufferError(Exception):
    pass


class EOFError(Exception):
    pass


class ImportError(Exception):
    def __init__(self, *args, name=None, path=None):
        Exception.__init__(self, *args)
        self.name = name
        self.path = path


class ModuleNotFoundError(ImportError):
    pass


class LookupError(Exception):
    pass


class IndexError(LookupError):
    pass


class KeyError(LookupError):
    pass


class MemoryError(Exception):
    pass


class NameError(Exception):
    pass


class UnboundLocalError(NameError):
    pass


class OSError(Exception):
    pass


class ReferenceError(Exception):
    pass


class RuntimeError(Exception):
    pass


class NotImplementedError(RuntimeError):
    pass


class RecursionError(RuntimeError):
    pass


class SyntaxError(Exception):
    pass


class SystemError(Exception):
    pass


class TypeError(Exception):
    pass


class ValueError(Exception):
    pass


# endregion


# region: Builtin Functions


# Reference: https://docs.python.org/3/library/functions.html


def abs(obj):
    return CALL_SLOT(obj, "__abs__")


def all(iterable):
    for element in iterable:
        if not element:
            return False
    return True


def any(iterable):
    for element in iterable:
        if element:
            return True
    return False


def ascii(obj):
    raise NotImplementedError("builtin 'ascii' not implemented yet")


def bin(obj):
    raise NotImplementedError("builtin 'bin' not implemented yet")


def breakpoint(*args, **kwargs):
    HALT()


def callable(obj):
    if GET_SLOT(obj, "__call__") is not None:
        return True
    elif CLS_OF(obj) is function:
        return True
    else:
        return False


def compile(source, filename, mode, flags=0, dont_inherit=False, optimize=-1):
    raise NotImplementedError("builtin 'compile' not implemented yet")


def delattr(obj, name):
    delete_attribute(obj, name)


def dir(obj=None):
    raise NotImplementedError("builtin 'dir' not implemented yet")


def divmod(left, right):
    raise NotImplementedError("builtin 'divmod' not implemented yet")


def enumerate(iterable, start=0):
    for element in iterable:
        yield start, element
        start = start + 1


def eval(expression, globals=None, locals=None):
    raise NotImplementedError("builtin 'eval' not implemented yet")


def exec(obj, globals=None, locals=None):
    raise NotImplementedError("builtin 'exec' not implemented yet")


def filter(function, iterable):
    for element in iterable:
        if function(element):
            yield element


def format(value, format_spec=None):
    return CALL_SLOT(value, "__format__", format_spec)


def getattr(obj, name, default=SENTINEL):
    try:
        if lowlevel_isinstance(name, str):
            return get_attribute(obj, name)
        else:
            raise TypeError()
    except AttributeError:
        if default is SENTINEL:
            raise
        return default


def globals():
    raise NotImplementedError("builtin 'globals' not implemented yet")


def hasattr(obj, name):
    try:
        get_attribute(obj, name)
        return True
    except AttributeError:
        return False


def hash(obj):
    return CALL_SLOT(obj, "__hash__")


def help(obj=SENTINEL):
    raise NotImplementedError("builtin 'help' not implemented yet")


def hex(obj):
    raise NotImplementedError("builtin 'hex' not implemented yet")


def id(obj):
    return NEW_FROM_VALUE(int, reference_id(obj))


def input(prompt=None):
    raise NotImplementedError("builtin 'input' not implemented yet")


def isinstance(obj, classinfo):
    if lowlevel_isinstance(classinfo, tuple):
        for element in classinfo:
            if isinstance(obj, element):
                return True
        return False
    else:
        return CALL_SLOT(classinfo, "__instancecheck__", obj)


def issubclass(cls, classinfo):
    if lowlevel_isinstance(classinfo, tuple):
        for element in classinfo:
            if issubclass(cls, element):
                return True
        return False
    else:
        return CALL_SLOT(classinfo, "__subclasscheck__", cls)


def iter(obj, sentinel=SENTINEL):
    if sentinel is SENTINEL:
        return runtime_iter(obj)
    else:
        raise NotImplementedError("'iter' with sentinel not implemented yet")


def len(obj):
    result = CALL_SLOT(obj, "__len__")
    length = CALL_SLOT(result, "__index__")
    if length < 0:
        raise ValueError()
    return length


def locals():
    raise NotImplementedError("builtin 'locals' not implemented yet")


def map(function, iterable, *iterables):
    if iterables:
        raise NotImplementedError("multiple iterables not supported yet")
    for element in iterable:
        yield function(element)


def max(*args, key=None, default=None):
    raise NotImplementedError("builtin 'max' not implemented yet")


def min(*args, key=None, default=None):
    raise NotImplementedError("builtin 'min' not implemented yet")


def next(obj, default=SENTINEL):
    try:
        return CALL_SLOT(obj, "__next__")
    except StopIteration:
        if default is SENTINEL:
            raise
        else:
            return default


def oct(obj):
    raise NotImplementedError("builtin 'oct' not implemented yet")


def open(
    file,
    mode="r",
    buffering=-1,
    encoding=None,
    errors=None,
    newline=None,
    closefd=True,
    opener=None,
):
    raise NotImplementedError("builtin 'open' not implemented yet")


def ord(char):
    raise NotImplementedError("builtin 'ord' not implemented yet")


def print(*objects, sep=" ", end="\n", file=None, flush=False):
    # the `file` and `flush` arguments do not do anything
    chunks = LITERAL(())
    for obj in objects:
        slot = GET_SLOT(obj, "__str__")
        if slot is None:
            raise ValueError()
        chunks = sequence_push(chunks, VALUE_OF(slot(obj)))
    # use the PRINT macro to print a string to the console
    PRINT(string_concat(string_join(VALUE_OF(sep), chunks), VALUE_OF(end)))


class property:
    def __init__(self, fget=None, fset=None, fdel=None, doc=None):
        if doc is not None:
            self.__doc__ = doc
        elif fget is not None:
            self.__doc__ = fget.__doc__
        self.fget = fget
        self.fset = fset
        self.fdel = fdel

    def getter(self, fget):
        return property(fget, self.fset, self.fdel, self.__doc__)

    def setter(self, fset):
        return property(self.fget, fset, self.fdel, self.__doc__)

    def deleter(self, fdel):
        return property(self.fget, self.fset, fdel, self.__doc__)

    def __get__(self, instance, owner=None):
        if instance is None:
            raise TypeError()
        return self.fget(instance)

    def __set__(self, instance, value):
        self.fset(instance, value)

    def __delete__(self, instance):
        self.fdel(instance)


def repr(obj):
    result = CALL_SLOT(obj, "__repr__")
    if lowlevel_isinstance(result, str):
        return result
    else:
        raise TypeError()


def reversed(obj):
    # TODO: implementation for the sequence protocol
    return CALL_SLOT(obj, "__reversed__")


def round(number, ndigits=None):
    raise NotImplementedError("builtin 'round' not implemented yet")


def setattr(obj, name, value):
    set_attribute(obj, name, value)


def sorted(iterable, *, key=None, reverse=False):
    raise NotImplementedError("builtin 'sorted' not implemented yet")


class staticmethod:
    def __init__(self, __func__):
        self.__func__ = __func__

    def __get__(self, instance, owner=None):
        return self.__func__


class classmethod:
    def __init__(self, __func__):
        self.__func__ = __func__

    def __get__(self, instance, owner=None):
        return BoundMethod(
            self.__func__, owner if owner is not None else CLS_OF(instance)
        )


def sum(iterable, start=0):
    raise NotImplementedError("builtin 'sum' not implemented yet")


class super:
    def __new__(cls, typ=None, object_or_type=None):
        attributes = NEW_FROM_VALUE(mappingproxy, LITERAL({}))
        attributes["__thisclass__"] = typ
        if typ is not None and not lowlevel_isinstance(typ, type):
            raise TypeError("super(): `typ` is not an instance of `type`")
        attributes["__self__"] = object_or_type
        if object_or_type is None:
            attributes["__self_class__"] = None
        elif lowlevel_isinstance(object_or_type, type):
            if not lowlevel_issubclass(object_or_type, typ):
                raise TypeError("super(): `object_or_type` is not a subclass of `type`")
            attributes["__self_class__"] = object_or_type
        else:
            if not lowlevel_isinstance(object_or_type, typ):
                raise TypeError(
                    "super(): `object_or_type` is not an instance of `type`"
                )
            attributes["__self_class__"] = CLS_OF(object_or_type)
        return NEW(RECORD(cls=super, dict=attributes))

    def __init__(self, typ=None, object_or_type=None):
        if typ is None:
            raise SystemError()

    def __getattribute__(self, name):
        if not lowlevel_isinstance(name, str):
            raise TypeError("super(): getattribute `name` is not a string")
        if VALUE_OF(name) != LITERAL("__class__"):
            attributes = record_get(LOAD(self), LITERAL("dict"))
            start_type = attributes["__self_class__"]
            this_class = attributes["__thisclass__"]
            if start_type is not None:
                mro = record_get(LOAD(start_type), LITERAL("mro"))

                # compute offset to `this_class`
                length = sequence_length(mro)
                index = LITERAL(0)
                while index < length:
                    if sequence_get(mro, index) is this_class:
                        break
                    index = number_add(index, LITERAL(1))

                # skip `this_class` itself
                index = number_add(index, LITERAL(1))

                # now begin searching the MRO starting after `this_class`
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
                                instance = attributes["__self__"]
                                if instance is start_type:
                                    instance = None
                                return descriptor_get(value, instance, start_type)
                    index = number_add(index, LITERAL(1))

        return object.__getattribute__(self, name)


def vars(obj=SENTINEL):
    raise NotImplementedError("builtin 'vars' not implemented yet")


def zip(*iterables):
    raise NotImplementedError("builtin 'zip' not implemented yet")


def __import__(name, globals=None, locals=None, fromlist=None, level=0):
    raise NotImplementedError("builtin '__import__' not implemented yet")


# endregion


# region: Other Builtins


def __build_class__(func, name, *bases, metaclass=None, **kwargs):
    mcs = extract_metaclass(unpack_iterable(bases))
    if metaclass is None:
        metaclass = mcs
    else:
        if lowlevel_isinstance(metaclass, type):
            if lowlevel_issubclass(metaclass, mcs):
                mcs = metaclass
            elif not lowlevel_issubclass(mcs, metaclass):
                raise TypeError("incompatible meta classes")
            else:
                metaclass = mcs

    prepare = GET_CLS_SLOT(mcs, "__prepare__")
    if prepare is None:
        raise TypeError()
    namespace = prepare(name, bases, **kwargs)

    class_cell = Cell()

    # inject cell for `__class__`
    func_descriptor = LOAD(func)
    STORE(
        func,
        record_set(
            func_descriptor,
            LITERAL("cells"),
            mapping_set(
                record_get(func_descriptor, LITERAL("cells")),
                LITERAL("__class__"),
                class_cell,
            ),
        ),
    )

    func(namespace)
    cls = metaclass(name, bases, namespace, **kwargs)
    class_cell.set_value(cls)
    return cls


# endregion


# region: SOS Python Debugging Builtins


def __print_load__(obj):
    PRINT(LOAD(obj))
    return obj


def __print_primitive__(obj):
    PRINT(obj)
    return obj


# endregion


# region: Lambda-Py Assert Builtins


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
        assert False
    assert False


# endregion
