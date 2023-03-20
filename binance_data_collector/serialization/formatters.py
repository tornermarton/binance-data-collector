# coding=utf-8
import abc
import csv
import dataclasses
import enum
import io
from pathlib import Path
from typing import Optional, Type, cast, Iterable, Any, overload

import jsons
import ujson as json
from ruamel.yaml import YAML

from .core import StateHolder, T


class Formatter(metaclass=abc.ABCMeta):
    def __init__(self, fork_inst: Type[StateHolder] = StateHolder) -> None:
        self._fork_inst: Type[StateHolder] = fork_inst

    @abc.abstractmethod
    def _convert_obj_to_str(self, data: object) -> str:
        pass

    @abc.abstractmethod
    def _convert_str_to_obj(self, data: str) -> object:
        pass

    @overload
    def dump(self, obj: dict, **kwargs) -> dict:
        ...

    @overload
    def dump(self, obj: list, **kwargs) -> list:
        ...

    def dump(self, obj: object, **kwargs) -> dict:
        return jsons.dump(obj, fork_inst=self._fork_inst, **kwargs)  # noqa

    def load(self, obj: object, cls: Type[T], **kwargs) -> T:
        return jsons.load(obj, cls=cls, fork_inst=self._fork_inst, **kwargs)

    def dumps(self, obj: T, **kwargs) -> str:
        return self._convert_obj_to_str(self.dump(obj, **kwargs))

    def loads(self, obj: str, cls: Type[T], **kwargs) -> T:
        return self.load(self._convert_str_to_obj(data=obj), cls=cls, **kwargs)

    def dumpb(self, obj: T, encoding: str = "utf-8", **kwargs) -> bytes:
        return self.dumps(obj, **kwargs).encode(encoding=encoding)

    def loadb(self, obj: bytes, cls: Type[T], encoding: str = "utf-8", **kwargs) -> T:
        return self.loads(obj.decode(encoding=encoding), cls=cls, **kwargs)

    def write(self, path: Path, obj: object, **kwargs) -> None:
        path.write_text(self.dumps(obj, **kwargs))

    def read(self, path: Path, cls: Type[T], **kwargs) -> T:
        return self.loads(path.read_text(), cls=cls, **kwargs)


class Parameters(object):
    def as_dict(self) -> dict:
        return {key: value for key, value in self.__dict__ if value is not None}


@dataclasses.dataclass
class JsonParameters(Parameters):
    skipkeys: Optional[bool] = None
    ensure_ascii: Optional[bool] = None
    check_circular: Optional[bool] = None
    allow_nan: Optional[bool] = None
    indent: Optional[int] = None
    separators: Optional[tuple[str]] = None
    default: Optional[callable] = None
    sort_keys: Optional[bool] = None


class JsonFormatter(Formatter):
    def __init__(
        self,
        parameters: JsonParameters = JsonParameters(),
        fork_inst: Type[StateHolder] = StateHolder,
    ) -> None:
        super().__init__(fork_inst)

        self._parameters: JsonParameters = parameters

    def _convert_obj_to_str(self, data: object) -> str:
        return json.dumps(
            data,
            **cast(
                dict,
                jsons.dump(
                    self._parameters,
                    cls=JsonParameters,
                    strip_nulls=True,
                ),
            ),
        )

    def _convert_str_to_obj(self, data: str) -> object:
        return json.loads(
            data,
            **cast(
                dict,
                jsons.dump(
                    self._parameters,
                    cls=JsonParameters,
                    strip_nulls=True,
                ),
            ),
        )


@dataclasses.dataclass
class YamlParameters(Parameters):
    mapping: int = 4
    sequence: int = 4
    offset: int = 2


class YamlFormatter(Formatter):
    def __init__(
        self,
        parameters: YamlParameters = YamlParameters(),
        fork_inst: Type[StateHolder] = StateHolder,
    ) -> None:
        super().__init__(fork_inst)

        self._parameters: YamlParameters = parameters

    def _convert_obj_to_str(self, data: object) -> str:
        yaml_container = io.StringIO()

        yaml = YAML()
        yaml.indent(
            mapping=self._parameters.mapping,
            sequence=self._parameters.sequence,
            offset=self._parameters.offset,
        )
        yaml.dump(data=data, stream=yaml_container)

        return yaml_container.getvalue()

    def _convert_str_to_obj(self, data: str) -> object:
        return YAML(typ="safe").load(data)


class DataFormatter(object):
    def __init__(self, parameters: Optional[Parameters] = None) -> None:
        self._parameters: Optional[Parameters] = parameters


class QUOTING(enum.IntEnum):
    QUOTE_ALL = csv.QUOTE_ALL
    QUOTE_MINIMAL = csv.QUOTE_MINIMAL
    QUOTE_NONE = csv.QUOTE_NONE
    QUOTE_NONNUMERIC = csv.QUOTE_NONNUMERIC


@dataclasses.dataclass
class XSVParameters(Parameters):
    delimiter: Optional[str] = None
    doublequote: Optional[bool] = None
    escapechar: Optional[str] = None
    lineterminator: Optional[str] = None
    quotechar: Optional[str] = None
    quoting: Optional[QUOTING] = None
    skipinitialspace: Optional[bool] = None


class XSVDataFormatter(DataFormatter):
    def __init__(self, parameters: XSVParameters = XSVParameters()) -> None:
        super().__init__(parameters=parameters)

    def load_data(self, data: str) -> Iterable[Iterable[Any]]:
        reader = csv.reader(
            data.split(self._parameters.lineterminator), **self._parameters.as_dict()
        )

        return [line for line in reader if not (len(line) < 1)]

    def dump_data(self, data: Iterable[Iterable[Any]]) -> str:
        csv_container = io.StringIO()
        writer = csv.writer(csv_container, **self._parameters.as_dict())

        writer.writerows(data)

        return csv_container.getvalue()


@dataclasses.dataclass
class JsonDataFormatter(DataFormatter):
    def __init__(self, parameters: JsonParameters = JsonParameters()) -> None:
        super().__init__(parameters=parameters)

    def load_data(self, data: str) -> dict[str, Any]:
        return json.loads(data)

    def dump_data(self, data: dict[str, Any]) -> str:
        return json.dumps(data, **self._parameters.as_dict())


@dataclasses.dataclass
class YamlDataFormatter(DataFormatter):
    def __init__(self, parameters: YamlParameters = YamlParameters()) -> None:
        super().__init__(parameters=parameters)

    def load_data(self, data: str) -> dict[str, Any]:
        return YAML(typ="safe").load(data)

    def dump_data(self, data: dict[str, Any]) -> str:
        yaml_container = io.StringIO()

        yaml = YAML()
        yaml.indent(**self._parameters.as_dict())
        yaml.dump(data=data, stream=yaml_container)

        return yaml_container.getvalue()


@dataclasses.dataclass
class EnvDataFormatter(DataFormatter):
    def __init__(self) -> None:
        super().__init__(parameters=None)

    def load_data(self, data: str) -> dict[str, str]:
        # TODO: casting values (if needed)
        d = {}

        for line in data:
            line = line.strip()
            if not line.startswith("#") or line.strip() != "":
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                if key == "":
                    raise ValueError("Invalid key")

                d[key] = value if value != "" else None

        return d

    def dump_data(self, data: dict[str, Any]) -> str:
        # TODO: handle space in strings
        s = ""

        for key, value in data.items():
            s += f"{key}={value}"

        return s
