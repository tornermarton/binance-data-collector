# coding=utf-8
import abc
import dataclasses
from typing import Callable, Generic, MutableSequence, Optional, TypeVar, Union

import jsons


T = TypeVar("T")
StateHolder = jsons.fork()


class Serializer(Generic[T]):
    @abc.abstractmethod
    def __call__(self, obj: T, **_) -> object:
        pass


class Deserializer(Generic[T]):
    @abc.abstractmethod
    def __call__(self, obj: object, cls: type, **_) -> T:
        pass


@dataclasses.dataclass(frozen=True)
class ClassSerializer(Serializer[T]):
    strip_nulls: bool = False
    strip_privates: bool = False
    strip_properties: bool = True
    strip_class_variables: bool = True
    strip_attr: Optional[Union[str, MutableSequence[str], tuple[str]]] = None
    key_transformer: Optional[Callable[[str], str]] = None
    verbose: Union[jsons.Verbosity, bool] = False
    strict: bool = True

    def __call__(self, obj: T, **kwargs) -> dict:
        return jsons.default_object_serializer(
            **{
                **kwargs,
                "obj": obj,
                "strip_nulls": self.strip_nulls,
                "strip_privates": self.strip_privates,
                "strip_properties": self.strip_properties,
                "strip_class_variables": self.strip_class_variables,
                "strip_attr": self.strip_attr,
                "key_transformer": self.key_transformer,
                "verbose": self.verbose,
                "strict": self.strict,
            }
        )


@dataclasses.dataclass(frozen=True)
class ClassDeserializer(Deserializer[T]):
    key_transformer: Optional[Callable[[str], str]] = None
    strict: bool = True

    def __call__(self, obj: dict, cls: type, **kwargs) -> T:
        return jsons.default_object_deserializer(
            **{
                **kwargs,
                "obj": obj,
                "cls": cls,
                "key_transformer": self.key_transformer,
                "strict": self.strict,
            }
        )
