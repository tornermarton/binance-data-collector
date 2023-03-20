# coding=utf-8
from __future__ import annotations

import abc
import dataclasses
import typing
import uuid

T = typing.TypeVar("T")

NextObserver: typing.Type = typing.Callable[[T], None]
ErrorObserver: typing.Type = typing.Callable[[BaseException], None]
CompleteObserver: typing.Type = typing.Callable[[], None]


class SubscriptionAlreadyClosedException(Exception):
    pass


class SubjectAlreadyCompletedException(Exception):
    pass


@dataclasses.dataclass(frozen=True)
class Observer(typing.Generic[T]):
    on_next: typing.Optional[NextObserver] = None
    on_error: typing.Optional[ErrorObserver] = None
    on_complete: typing.Optional[CompleteObserver] = None


class Unsubscribable(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def unsubscribe(self) -> None:
        raise NotImplementedError()


class Subscribable(typing.Generic[T], metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def subscribe(
        self,
        on_next: typing.Optional[NextObserver] = None,
        on_error: typing.Optional[ErrorObserver] = None,
        on_complete: typing.Optional[CompleteObserver] = None,
    ) -> Unsubscribable:
        raise NotImplementedError()


UnsubscriptionCallback: typing.Type = typing.Callable[[], typing.Any]


class Subscription(Unsubscribable):
    def __init__(
        self,
        on_unsubscribe: typing.Optional[UnsubscriptionCallback] = None,
    ) -> None:
        self._on_unsubscribe: typing.Optional[UnsubscriptionCallback] = \
            on_unsubscribe

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


SubscriptionCallback: typing.Type = typing.Callable[
    [
        typing.Optional[NextObserver],
        typing.Optional[ErrorObserver],
        typing.Optional[CompleteObserver],
    ],
    typing.Optional[Subscription],
]


class Observable(Subscribable, typing.Generic[T]):
    def __init__(
        self,
        on_subscribe: typing.Optional[SubscriptionCallback] = None,
    ) -> None:
        self._on_subscribe: typing.Optional[SubscriptionCallback] = on_subscribe

    def subscribe(
        self,
        on_next: typing.Optional[NextObserver] = None,
        on_error: typing.Optional[ErrorObserver] = None,
        on_complete: typing.Optional[CompleteObserver] = None,
    ) -> Subscription:
        subscription: typing.Optional[Subscription] = None

        if self._on_subscribe is not None:
            subscription = self._on_subscribe(on_next, on_error, on_complete)

        if subscription is not None:
            return subscription

        return Subscription()


class Subject(Observable, typing.Generic[T]):
    def __init__(self) -> None:
        super().__init__()

        self._completed: bool = False
        self._observers: dict[int, Observer[T]] = {}

    def _check_completed(self) -> None:
        if self._completed:
            raise SubjectAlreadyCompletedException()

    def next(self, value: T) -> None:
        self._check_completed()

        for observer in list(self._observers.values()):
            if observer is not None and observer.on_next is not None:
                observer.on_next(value)

    def error(self, error: BaseException) -> None:
        self._check_completed()

        for observer in list(self._observers.values()):
            if observer is not None and observer.on_error is not None:
                observer.on_error(error)

    def complete(self) -> None:
        self._check_completed()

        self._completed = True

        for observer in list(self._observers.values()):
            if observer is not None and observer.on_complete is not None:
                observer.on_complete()

    @property
    def observed(self) -> bool:
        return len(self._observers) > 0

    def as_observable(self) -> Observable[T]:
        return Observable(on_subscribe=self.subscribe)

    def subscribe(
        self,
        on_next: typing.Optional[NextObserver] = None,
        on_error: typing.Optional[ErrorObserver] = None,
        on_complete: typing.Optional[CompleteObserver] = None,
    ) -> Subscription:
        key: int = uuid.uuid4().int
        observer: Observer = Observer(
            on_next=on_next,
            on_error=on_error,
            on_complete=on_complete,
        )
        self._observers[key] = observer

        subscription: Subscription = Subscription(
            on_unsubscribe=lambda: self._observers.pop(key),
        )

        return subscription


class BehaviorSubject(Subject):
    def __init__(self, value: T = None) -> None:
        super().__init__()

        self._value: T = value

    @property
    def value(self) -> T:
        return self._value

    def next(self, value: T) -> None:
        self._value = value

        return super().next(value=value)

    def subscribe(
        self,
        on_next: typing.Optional[NextObserver] = None,
        on_error: typing.Optional[ErrorObserver] = None,
        on_complete: typing.Optional[CompleteObserver] = None,
    ) -> Subscription:
        if on_next is not None:
            on_next(self._value)

        return super().subscribe(
            on_next=on_next,
            on_error=on_error,
            on_complete=on_complete,
        )


def _empty(observer: typing.Optional[Observer[...]] = None) -> Subscription:
    if observer is not None and observer.on_complete is not None:
        observer.on_complete()

    return Subscription()


EMPTY: Observable[None] = Observable(on_subscribe=_empty)
