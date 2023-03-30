# coding=utf-8
import abc
import dataclasses
import typing
from pathlib import Path

import jsons


T = typing.TypeVar("T")
D = typing.TypeVar("D")
StripAttrType = typing.Union[str, typing.MutableSequence[str], tuple[str]]
StateHolder = jsons.fork()


class Serializer(typing.Generic[T]):
    @abc.abstractmethod
    def __call__(self, obj: T, **_) -> object:
        pass


class Deserializer(typing.Generic[T]):
    @abc.abstractmethod
    def __call__(self, obj: object, cls: type, **_) -> T:
        pass


@dataclasses.dataclass(frozen=True)
class ClassSerializer(Serializer[T]):
    strip_nulls: bool = False
    strip_privates: bool = False
    strip_properties: bool = True
    strip_class_variables: bool = True
    strip_attr: typing.Optional[StripAttrType] = None
    key_transformer: typing.Optional[typing.Callable[[str], str]] = None
    verbose: typing.Union[jsons.Verbosity, bool] = False
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
    key_transformer: typing.Optional[typing.Callable[[str], str]] = None
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


class Parameters(object):
    def as_dict(self) -> dict:
        return {key: value for key, value in self.__dict__ if value is not None}


class Formatter(metaclass=abc.ABCMeta):
    def __init__(self, fork_inst: typing.Type[StateHolder] = StateHolder) -> None:
        self._fork_inst: typing.Type[StateHolder] = fork_inst

    @abc.abstractmethod
    def _convert_obj_to_str(self, data: object) -> str:
        pass

    @abc.abstractmethod
    def _convert_str_to_obj(self, data: str) -> object:
        pass

    @typing.overload
    def dump(self, obj: dict, **kwargs) -> dict:
        ...

    @typing.overload
    def dump(self, obj: list, **kwargs) -> list:
        ...

    def dump(self, obj: object, **kwargs) -> dict:
        return jsons.dump(obj, fork_inst=self._fork_inst, **kwargs)  # noqa

    def load(self, obj: object, cls: typing.Type[T], **kwargs) -> T:
        return jsons.load(obj, cls=cls, fork_inst=self._fork_inst, **kwargs)

    def dumps(self, obj: T, **kwargs) -> str:
        return self._convert_obj_to_str(self.dump(obj, **kwargs))

    def loads(self, obj: str, cls: typing.Type[T], **kwargs) -> T:
        return self.load(self._convert_str_to_obj(data=obj), cls=cls, **kwargs)

    def dumpb(self, obj: T, encoding: str = "utf-8", **kwargs) -> bytes:
        return self.dumps(obj, **kwargs).encode(encoding=encoding)

    def loadb(
        self,
        obj: bytes,
        cls: typing.Type[T],
        encoding: str = "utf-8",
        **kwargs,
    ) -> T:
        return self.loads(obj.decode(encoding=encoding), cls=cls, **kwargs)

    def write(self, path: Path, obj: object, **kwargs) -> None:
        path.write_text(self.dumps(obj, **kwargs))

    def read(self, path: Path, cls: typing.Type[T], **kwargs) -> T:
        return self.loads(path.read_text(), cls=cls, **kwargs)


class DataFormatter(typing.Generic[D], metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def load_data(self, data: str) -> D:
        raise NotImplementedError

    @abc.abstractmethod
    def dump_data(self, data: D) -> str:
        raise NotImplementedError
