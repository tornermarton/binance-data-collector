# coding=utf-8
import abc
import dataclasses
import datetime
import typing
from uuid import uuid4

from binance_data_collector.app.constants import TZ


class EntityNotFoundException(Exception):
    pass


class EntityAlreadyExistsException(Exception):
    pass


@dataclasses.dataclass(kw_only=True)
class Model(metaclass=abc.ABCMeta):
    uuid: str = dataclasses.field(default_factory=lambda: str(uuid4()))
    created_at: datetime.datetime = dataclasses.field(default_factory=lambda: datetime.datetime.now(tz=TZ))
    updated_at: datetime.datetime = dataclasses.field(default_factory=lambda: datetime.datetime.now(tz=TZ))


T = typing.TypeVar("T", bound=Model)


class Repository(typing.Generic[T], metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def find(self, query: dict[str, typing.Any] | None = None) -> list[T]:
        raise NotImplementedError

    @abc.abstractmethod
    def create(self, item: T) -> T:
        raise NotImplementedError

    @abc.abstractmethod
    def read(self, uuid: str) -> T:
        raise NotImplementedError

    @abc.abstractmethod
    def update(self, uuid: str, item: typing.Any) -> T:
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, uuid: str) -> None:
        raise NotImplementedError
