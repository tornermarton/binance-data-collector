# coding=utf-8
from __future__ import annotations

__all__ = ["DataFile", "DataFileManager", "create_data_file_manager"]

import contextlib
import datetime
import gzip
import threading
from pathlib import Path
from typing import Any, Optional

try:
    import ujson as json
except ImportError:
    import json

from binance_data_collector.app.models.currency_pair import CurrencyPair


lock: threading.Lock = threading.Lock()


class DataFile(object):
    def __init__(self, currency_pair: CurrencyPair, ts: datetime.date) -> None:
        self._currency_pair: CurrencyPair = currency_pair
        self._ts: datetime.date = ts

        self._file: Optional[gzip.GzipFile] = None

    @property
    def ts(self) -> datetime.date:
        return self._ts

    @property
    def file(self):
        return self._file

    def open(self, root: Path, pattern: str) -> gzip.GzipFile:
        # prevent broken files and lost ios
        if self._file is not None:
            self._file.close()

        path = root / self._currency_pair.lower() / pattern.format(ts=self._ts)
        path.parent.mkdir(parents=True, exist_ok=True)

        self._file = gzip.open(path, mode="ab")

        return self._file

    def close(self) -> None:
        if self._file is not None:
            self._file.close()

    def write_data(self, data: dict[str, Any]) -> None:
        self._file.write(json.dumps(data).encode('utf8'))
        self._file.write(b'\n')


class DataFileManager(object):
    def __init__(self, data_root: Path, pattern: str) -> None:
        self._data_root: Path = data_root
        self._pattern: str = pattern

        self._data_files: dict[str, DataFile] = {}

    def get_file(self, currency_pair: CurrencyPair) -> DataFile:
        with lock:
            key: str = currency_pair.lower()
            ts: datetime.date = datetime.date.today()

            if key in self._data_files and ts != self._data_files[key].ts:
                # close before switch to prevent non-closed io at exception
                self._data_files[key].close()

                del self._data_files[key]

            if key not in self._data_files:
                self._data_files[key] = DataFile(
                    currency_pair=currency_pair,
                    ts=ts,
                )

                # open only after assign to prevent non-closed io at exception
                self._data_files[key].open(
                    root=self._data_root,
                    pattern=self._pattern,
                )

            return self._data_files[key]

    def stop(self) -> None:
        for data_file in self._data_files.values():
            data_file.close()


@contextlib.contextmanager
def create_data_file_manager(path: Path, name: str) -> DataFileManager:
    manager: DataFileManager = DataFileManager(
        data_root=path,
        pattern=f"{name}.{{ts}}.json.gz"
    )

    try:
        yield manager
    except:
        manager.stop()
