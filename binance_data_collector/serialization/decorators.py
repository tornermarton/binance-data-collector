# coding=utf-8
import typing

import jsons

from .core import ClassDeserializer, ClassSerializer, StateHolder, T


def _set_serializer(cls: typing.Type[T], serializer: ClassSerializer[T]) -> None:
    cls.__serializer__ = serializer


def _pop_serializer(cls: typing.Type[T]) -> ClassSerializer:
    if hasattr(cls, "__serializer__"):
        serializer = cls.__serializer__
        del cls.__serializer__
    else:
        serializer = ClassSerializer()

    return serializer


def _set_deserializer(cls: typing.Type[T], deserializer: ClassDeserializer[T]) -> None:
    cls.__deserializer__ = deserializer


def _pop_deserializer(cls: typing.Type[T]) -> ClassDeserializer[T]:
    if hasattr(cls, "__deserializer__"):
        deserializer = cls.__deserializer__
        del cls.__deserializer__
    else:
        deserializer = ClassDeserializer()

    return deserializer


def with_serializer(
    serializer: ClassSerializer[T],
) -> typing.Callable[[typing.Type[T]], typing.Type[T]]:
    def class_wrapper(cls: typing.Type[T]) -> typing.Type[T]:
        _set_serializer(cls=cls, serializer=serializer)

        return cls

    return class_wrapper


def with_deserializer(
    deserializer: ClassDeserializer[T],
) -> typing.Callable[[typing.Type[T]], typing.Type[T]]:
    def class_wrapper(cls: typing.Type[T]) -> typing.Type[T]:
        _set_deserializer(cls=cls, deserializer=deserializer)

        return cls

    return class_wrapper


def with_dump(
    strip_nulls: bool = False,
    strip_privates: bool = False,
    strip_properties: bool = True,
    strip_class_variables: bool = True,
    strip_attr: typing.Optional[typing.Union[str, typing.MutableSequence[str], tuple[str]]] = None,
    key_transformer: typing.Optional[typing.Callable[[str], str]] = None,
    verbose: typing.Union[jsons.Verbosity, bool] = False,
    strict: bool = True,
) -> typing.Callable[[typing.Type[T]], typing.Type[T]]:
    serializer = ClassSerializer(
        strip_nulls=strip_nulls,
        strip_privates=strip_privates,
        strip_properties=strip_properties,
        strip_class_variables=strip_class_variables,
        strip_attr=strip_attr,
        key_transformer=key_transformer,
        verbose=verbose,
        strict=strict,
    )

    return with_serializer(serializer=serializer)


def with_load(
    key_transformer: typing.Optional[typing.Callable[[str], str]] = None,
    strict: bool = True,
) -> typing.Callable[[typing.Type[T]], typing.Type[T]]:
    deserializer = ClassDeserializer(
        key_transformer=key_transformer,
        strict=strict,
    )

    return with_deserializer(deserializer=deserializer)


def _clean_dataclass_class_variables(cls: typing.Type[T]) -> None:
    for name in cls.__dict__.get("__dataclass_fields__", {}):
        # starting from root clean all parent classes
        for cls_ in [*reversed(cls.__bases__), cls]:
            if hasattr(cls_, name):
                delattr(cls_, name)

            if hasattr(cls_, "__annotations__"):
                cls.__annotations__.pop(name, None)


def serializable(
    fork_inst: typing.Type[StateHolder] = StateHolder,
) -> typing.Callable[[typing.Type[T]], typing.Type[T]]:
    def class_wrapper(cls: typing.Type[T]) -> typing.Type[T]:
        _clean_dataclass_class_variables(cls=cls)

        jsons.set_serializer(
            _pop_serializer(cls=cls),
            cls=cls,
            fork_inst=fork_inst,
        )
        jsons.set_deserializer(
            _pop_deserializer(cls=cls),
            cls=cls,
            fork_inst=fork_inst,
        )

        return cls

    return class_wrapper
