# coding=utf-8
import dataclasses
import typing

from .types import InjectionToken


@dataclasses.dataclass(frozen=True)
class Inject(object):
    token: InjectionToken


@dataclasses.dataclass(frozen=True)
class ValueProvider(object):
    provide: InjectionToken
    use_value: typing.Any


@dataclasses.dataclass(frozen=True)
class ClassProvider(object):
    provide: InjectionToken
    use_class: typing.Type


@dataclasses.dataclass(frozen=True)
class FactoryProvider(object):
    provide: InjectionToken
    use_factory: typing.Callable


TypeProvider: typing.TypeAlias = typing.Type
BasicProvider: typing.TypeAlias = ValueProvider | ClassProvider | FactoryProvider
ProviderLike = TypeProvider | BasicProvider
