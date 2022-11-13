# coding=utf-8
from __future__ import annotations

import abc
import dataclasses
import typing
import uuid

T = typing.TypeVar("T")


class SubscriptionAlreadyClosedException(Exception):
    pass


class SubjectAlreadyCompletedException(Exception):
    pass


@dataclasses.dataclass(frozen=True)
class Observer(typing.Generic[T]):
    next: typing.Optional[typing.Callable[[T], None]] = None
    error: typing.Optional[typing.Callable[[BaseException], None]] = None
    complete: typing.Optional[typing.Callable[[], None]] = None


class Unsubscribable(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def unsubscribe(self) -> None:
        raise NotImplementedError()


class Subscribable(typing.Generic[T], metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def subscribe(
        self,
        observer: typing.Optional[Observer[T]] = None,
    ) -> Unsubscribable:
        raise NotImplementedError()


class Subscription(Unsubscribable):
    def __init__(
        self,
        on_unsubscribe: typing.Optional[typing.Callable[[], ...]] = None,
    ) -> None:
        self._on_unsubscribe: typing.Optional[
            typing.Callable[[], ...]
        ] = on_unsubscribe

        self._closed: bool = False

    @property
    def closed(self) -> bool:
        return self._closed

    def unsubscribe(self) -> None:
        if self._closed:
            return

        if self._on_unsubscribe is not None:
            self._on_unsubscribe()

        self._closed = True


class Observable(Subscribable, typing.Generic[T]):
    def __init__(
        self,
        on_subscribe: typing.Optional[
            typing.Callable[
                [typing.Optional[Observer[T]]], typing.Optional[Subscription]
            ]
        ] = None,
    ) -> None:
        self._on_subscribe: typing.Optional[
            typing.Callable[
                [typing.Optional[Observer[T]]], typing.Optional[Subscription]
            ]
        ] = on_subscribe

    def subscribe(
        self,
        observer: typing.Optional[Observer[T]] = None,
    ) -> Subscription:
        subscription: typing.Optional[Subscription] = None

        if self._on_subscribe is not None:
            subscription = self._on_subscribe(observer)

        if subscription is not None:
            return subscription

        return Subscription()


class Subject(Observable, typing.Generic[T]):
    def __init__(self, value: typing.Optional[T] = None) -> None:
        super().__init__()

        self._value: typing.Optional[T] = value

        self._completed: bool = False
        self._observers: dict[int, Observer[T]] = {}

    @property
    def value(self) -> T:
        return self._value

    def next(self, value: T) -> None:
        if self._completed:
            raise SubjectAlreadyCompletedException(
                "Subject is already completed"
            )

        self._value = value

        for observer in self._observers.values():
            if observer is not None and observer.next is not None:
                observer.next(value)

    def error(self, error: BaseException) -> None:
        if self._completed:
            raise SubjectAlreadyCompletedException(
                "Subject is already completed"
            )

        for observer in self._observers.values():
            if observer is not None and observer.error is not None:
                observer.error(error)

    def complete(self) -> None:
        self._completed = True

        for observer in self._observers.values():
            if observer is not None and observer.complete is not None:
                observer.complete()

    @property
    def observed(self) -> bool:
        return len(self._observers) > 0

    def as_observable(self) -> Observable[T]:
        return Observable(on_subscribe=self.subscribe)

    def subscribe(
        self,
        observer: typing.Optional[Observer[T]] = None,
    ) -> Subscription:
        key: int = uuid.uuid4().int
        self._observers[key] = observer

        subscription: Subscription = Subscription(
            on_unsubscribe=lambda: self._observers.pop(key),
        )

        if observer is not None and self._value is not None:
            observer.next(self._value)

        return subscription


def _empty(observer: typing.Optional[Observer[...]] = None) -> Subscription:
    if observer is not None and observer.complete is not None:
        observer.complete()

    return Subscription()


EMPTY: Observable[None] = Observable(on_subscribe=_empty)
