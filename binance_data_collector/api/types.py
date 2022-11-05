# coding=utf-8
import typing

InjectionToken: typing.TypeAlias = type | str

ControllerLike = typing.NewType("ControllerLike", type)
ModuleLike = typing.NewType("ModuleLike", type)
