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

    def get_value(self) -> typing.Any:
        return self.use_value


@dataclasses.dataclass(frozen=True)
class ClassProvider(object):
    provide: InjectionToken
    use_class: typing.Type

    def get_value(self) -> typing.Any:
        # TODO: dependencies
        return self.use_class()


@dataclasses.dataclass(frozen=True)
class FactoryProvider(object):
    provide: InjectionToken
    use_factory: typing.Callable

    def get_value(self) -> typing.Any:
        # TODO: dependencies
        return self.use_factory()


TypeProvider: typing.TypeAlias = typing.Type
BasicProvider: typing.TypeAlias = ValueProvider | ClassProvider | FactoryProvider
ProviderLike = TypeProvider | BasicProvider
