# coding=utf-8
__all__ = ["ConfigType", "Config"]

import enum
import typing
from pathlib import Path

from ruamel.yaml import YAML

try:
    import ujson as json
except ImportError:
    import json

from .injection import ValueProvider
from .injectable import Injectable


class ConfigType(enum.Enum):
    YAML = enum.auto()
    JSON = enum.auto()


def load_config(path: Path, config_type: ConfigType) -> dict[str, typing.Any]:
    text: str = path.read_text()

    if config_type == ConfigType.YAML:
        return YAML().load(text)
    elif config_type == ConfigType.JSON:
        return json.loads(text)
    else:
        raise RuntimeError(f"Unsupported config type: `{config_type}`")


@Injectable()
class Config(object):
    @staticmethod
    def for_root(
        path: Path,
        config_type: ConfigType = ConfigType.YAML,
    ) -> ValueProvider:
        path = path.resolve()

        config: dict[str, typing.Any] = load_config(
            path=path,
            config_type=config_type,
        )

        return ValueProvider(
            provide=Config.__name__,
            use_value=Config(config=config),
        )

    def __init__(self, config: dict[str, typing.Any]) -> None:
        self._config = config

    def get(self, key: str) -> typing.Any:
        return self._config[key]
