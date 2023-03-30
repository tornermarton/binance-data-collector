# coding=utf-8
__all__ = ["environment"]

import os
import pathlib
import typing

from binance_data_collector.serialization import EnvFormatter


def load_dot_env():
    path: pathlib.Path = pathlib.Path.cwd().resolve() / ".env"

    if path.is_file():
        dot_env: dict[str, typing.Any] = EnvFormatter().loads(
            obj=path.read_text(),
            cls=dict[str, typing.Any],
        )

        for key, value in dot_env.items():
            os.environ[key] = value


load_dot_env()


class environment:
    data_root: str = os.environ.get("DATA_ROOT", "/data")
    data_file_name_pattern: str = os.environ.get("DATA_FILE_NAME_PATTERN", "{name}_{ts}.json.gz")
    snapshot_period_s: int = int(os.environ.get("SNAPSHOT_PERIOD_S", "60"))
