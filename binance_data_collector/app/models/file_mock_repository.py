# coding=utf-8
import datetime
import threading
import typing
from pathlib import Path

from binance_data_collector.app.constants import TZ
from binance_data_collector.serialization import JsonFormatter

from binance_data_collector.app.models.repository import (
    EntityAlreadyExistsException,
    EntityNotFoundException,
    Repository,
    T,
)


class FileMockRepository(typing.Generic[T], Repository[T]):
    def __init__(self, path: Path) -> None:
        self._path: Path = path

        self._formatter: JsonFormatter = JsonFormatter()
        # cache entries since collection is small
        self._entries: dict[str, T] = {}

        self._lock: threading.Lock = threading.Lock()

    def load(self) -> None:
        """This is a hack since s__orig_class__ is created after __init__()"""

        with self._lock:
            if not self._path.exists():
                self._path.write_text('{}')

            text: str = self._path.read_text()

            self._entries: dict[str, T] = self._formatter.loads(
                obj=text,
                cls=dict[str, typing.get_args(self.__orig_class__)[0]],
            )

    def _update_file(self) -> None:
        self._path.write_text(self._formatter.dumps(obj=self._entries))

    def _is_match(self, item: T, query: dict[str, typing.Any]) -> bool:
        return all(
            [
                getattr(item, key) == value
                for key, value in query.items()
                if value is not None
            ]
        )

    def find(self, query: dict[str, typing.Any] | None = None) -> list[T]:
        with self._lock:
            return [
                item for item in list(self._entries.values())
                if query is None or self._is_match(item=item, query=query)
            ]

    def create(self, item: T) -> T:
        with self._lock:
            if self._entries.get(item.uuid, None) is not None:
                raise EntityAlreadyExistsException()

            self._entries[item.uuid] = item

            self._update_file()

            return item

    def read(self, uuid: str) -> T:
        with self._lock:
            if self._entries.get(uuid, None) is None:
                raise EntityNotFoundException()

            return self._entries[uuid]

    def update(self, uuid: str, item: T) -> T:
        with self._lock:
            if self._entries.get(item.uuid, None) is None:
                raise EntityNotFoundException()

            item.updated_at = datetime.datetime.now(tz=TZ)
            self._entries[uuid] = item

            self._update_file()

            return item

    def delete(self, uuid: str) -> None:
        with self._lock:
            self._entries.pop(uuid, None)

            self._update_file()
