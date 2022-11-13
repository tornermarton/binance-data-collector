# coding=utf-8
__all__ = ["DataFile", "DataFileManager"]

import datetime
import gzip
import threading
from pathlib import Path
from typing import Any

try:
    import ujson as json
except ImportError:
    import json

from binance_data_collector.api import Injectable
from binance_data_collector.api.config import Config
from binance_data_collector.api.lifecycle import OnDestroy

from binance_data_collector.app.models.currency_pair import CurrencyPair


lock: threading.Lock = threading.Lock()


class DataFile(object):
    def __init__(self, path: Path, ts: datetime.date) -> None:
        self._path: Path = path
        self._ts: datetime.date = ts

        self._file: gzip.GzipFile | None = None

    @property
    def ts(self) -> datetime.date:
        return self._ts

    @property
    def file(self) -> gzip.GzipFile | None:
        return self._file

    def open(self) -> gzip.GzipFile:
        # prevent broken files and lost ios
        if self._file is not None:
            self._file.close()

        self._file = gzip.open(self._path, mode="ab")

        return self._file

    def close(self) -> None:
        if self._file is not None:
            self._file.close()

    def write_data(self, data: dict[str, Any]) -> None:
        self._file.write(json.dumps(data).encode('utf8'))
        self._file.write(b'\n')


@Injectable()
class DataFileManager(OnDestroy):
    def __init__(self, config: Config) -> None:
        self._data_root: Path = Path(config.get("data_root")).resolve()
        self._pattern: str = config.get("data_file_name_pattern")

        self._data_files: dict[str, DataFile] = {}

    def get_file(self, currency_pair: CurrencyPair, name: str) -> DataFile:
        key: str = f"{currency_pair.lower()}_{name}"
        ts: datetime.date = datetime.date.today()
        file_name: str = self._pattern.format(name=name, ts=ts)

        with lock:
            if key in self._data_files and ts != self._data_files[key].ts:
                # close before switch to prevent non-closed io at exception
                self._data_files[key].close()

                del self._data_files[key]

            if key not in self._data_files:
                path: Path = self._data_root / currency_pair.lower() / file_name

                self._data_files[key] = DataFile(path=path, ts=ts)

                path.parent.mkdir(parents=True, exist_ok=True)
                # open only after assign to prevent non-closed io at exception
                self._data_files[key].open()

            return self._data_files[key]

    def close_file(self, currency_pair: CurrencyPair, name: str) -> None:
        key: str = f"{currency_pair.lower()}_{name}"

        with lock:
            if key in self._data_files:
                # close before switch to prevent non-closed io at exception
                self._data_files[key].close()

                del self._data_files[key]

    def on_destroy(self) -> None:
        with lock:
            for key, data_file in tuple(self._data_files.items()):
                data_file.close()
                del self._data_files[key]
