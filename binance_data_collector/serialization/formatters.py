# coding=utf-8
import csv
import dataclasses
import enum
import io
import typing

import jsons
from ruamel.yaml import YAML

try:
    import ujson as json
except ImportError:
    import json

from .core import DataFormatter, Formatter, Parameters, StateHolder


@dataclasses.dataclass(frozen=True, kw_only=True)
class JsonParameters(Parameters):
    skipkeys: typing.Optional[bool] = None
    ensure_ascii: typing.Optional[bool] = None
    check_circular: typing.Optional[bool] = None
    allow_nan: typing.Optional[bool] = None
    indent: typing.Optional[int] = None
    separators: typing.Optional[tuple[str]] = None
    default: typing.Optional[callable] = None
    sort_keys: typing.Optional[bool] = None


class JsonFormatter(Formatter):
    def __init__(
        self,
        parameters: JsonParameters = JsonParameters(),
        fork_inst: typing.Type[StateHolder] = StateHolder,
    ) -> None:
        super().__init__(fork_inst)

        self._parameters: JsonParameters = parameters

    def _convert_obj_to_str(self, data: object) -> str:
        return json.dumps(
            data,
            **typing.cast(
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
            **typing.cast(
                dict,
                jsons.dump(
                    self._parameters,
                    cls=JsonParameters,
                    strip_nulls=True,
                ),
            ),
        )


@dataclasses.dataclass(frozen=True, kw_only=True)
class YamlParameters(Parameters):
    mapping: int = 4
    sequence: int = 4
    offset: int = 2


class YamlFormatter(Formatter):
    def __init__(
        self,
        parameters: YamlParameters = YamlParameters(),
        fork_inst: typing.Type[StateHolder] = StateHolder,
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


@dataclasses.dataclass(frozen=True, kw_only=True)
class EnvParameters(Parameters):
    line_terminator: typing.Optional[str] = None


class EnvFormatter(Formatter):
    def __init__(
        self,
        parameters: EnvParameters = EnvParameters(),
        fork_inst: typing.Type[StateHolder] = StateHolder,
    ) -> None:
        super().__init__(fork_inst=fork_inst)

        self._parameters: EnvParameters = parameters

    def _convert_obj_to_str(self, data: object) -> str:
        if type(data) != dict:
            raise TypeError("Env formatter can only handle flat dictionaries")

        data = typing.cast(typ=dict[str, typing.Any], val=data)

        t: str = self._parameters.line_terminator or '\n'

        return t.join([f"{key}=\"{value}\"" for key, value in data.items()])

    def _convert_str_to_obj(self, data: str) -> object:
        # TODO: casting values (if needed)
        d = {}

        lines: list[str] = data.split(self._parameters.line_terminator or '\n')

        for line in lines:
            line = line.strip()
            if not line.startswith("#") and not line.strip() == "":
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                if key == "":
                    raise ValueError("Invalid key")

                d[key] = value if value != "" else None

        return d


class XSVParametersQuoting(enum.IntEnum):
    QUOTE_ALL = csv.QUOTE_ALL
    QUOTE_MINIMAL = csv.QUOTE_MINIMAL
    QUOTE_NONE = csv.QUOTE_NONE
    QUOTE_NONNUMERIC = csv.QUOTE_NONNUMERIC


@dataclasses.dataclass(frozen=True, kw_only=True)
class XSVParameters(Parameters):
    delimiter: typing.Optional[str] = None
    doublequote: typing.Optional[bool] = None
    escapechar: typing.Optional[str] = None
    lineterminator: typing.Optional[str] = None
    quotechar: typing.Optional[str] = None
    quoting: typing.Optional[XSVParametersQuoting] = None
    skipinitialspace: typing.Optional[bool] = None


class XSVDataFormatter(DataFormatter[typing.Iterable[typing.Iterable[typing.Any]]]):
    def __init__(self, parameters: typing.Optional[XSVParameters] = None) -> None:
        self._parameters: XSVParameters = parameters or XSVParameters()

    def load_data(self, data: str) -> typing.Iterable[typing.Iterable[typing.Any]]:
        rows: list[str] = data.split(self._parameters.lineterminator or '\n')
        reader = csv.reader(rows, **self._parameters.as_dict())

        return [line for line in reader if not (len(line) < 1)]

    def dump_data(self, data: typing.Iterable[typing.Iterable[typing.Any]]) -> str:
        csv_container = io.StringIO()
        writer = csv.writer(csv_container, **self._parameters.as_dict())

        writer.writerows(data)

        return csv_container.getvalue()


class JsonDataFormatter(DataFormatter[typing.Iterable[dict[str, typing.Any]]]):
    def __init__(self, parameters: typing.Optional[JsonParameters] = None) -> None:
        self._parameters: JsonParameters = parameters or JsonParameters()

    def load_data(self, data: str) -> typing.Iterable[dict[str, typing.Any]]:
        rows: list[str] = data.split("\n")
        return [json.loads(r) for r in rows]

    def dump_data(self, data: typing.Iterable[dict[str, typing.Any]]) -> str:
        rows: list[str] = [json.dumps(d, **self._parameters.as_dict()) for d in data]
        return "\n".join(rows)
