# coding=utf-8
__all__ = ["PipeTransform", "UUIDVersion", "ParseUUIDPipe"]

import abc
import enum
import re
import typing

from .exceptions import HTTPException
from .http import HttpStatus

S = typing.TypeVar("S")
T = typing.TypeVar("T")


class PipeTransform(typing.Generic[S, T], metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def transform(self, value: S) -> T:
        raise NotImplementedError


class UUIDVersion(enum.Enum):
    V3 = "3"
    V4 = "4"
    V5 = "5"
    ALL = "ALL"


UUID_REGEXPS: dict[UUIDVersion, typing.Pattern] = {
    UUIDVersion.V3: re.compile(
        r"^[0-9A-F]{8}-[0-9A-F]{4}-3[0-9A-F]{3}-[0-9A-F]{4}-[0-9A-F]{12}$",
        flags=re.IGNORECASE,
    ),
    UUIDVersion.V4: re.compile(
        r"^[0-9A-F]{8}-[0-9A-F]{4}-4[0-9A-F]{3}-[89AB][0-9A-F]{3}-[0-9A-F]{12}$",
        flags=re.IGNORECASE,
    ),
    UUIDVersion.V5: re.compile(
        r"^[0-9A-F]{8}-[0-9A-F]{4}-5[0-9A-F]{3}-[89AB][0-9A-F]{3}-[0-9A-F]{12}$",
        flags=re.IGNORECASE,
    ),
    UUIDVersion.ALL: re.compile(
        r"^[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}$",
        flags=re.IGNORECASE,
    ),
}


class ParseUUIDPipe(PipeTransform[str, str]):
    def __init__(
        self,
        version: UUIDVersion = UUIDVersion.ALL,
        error_status_code: int = HttpStatus.BAD_REQUEST,
    ) -> None:
        self._version: UUIDVersion = version
        self._error_status_code: int = error_status_code

    def transform(self, value: typing.Any) -> str:
        if type(value) != str or UUID_REGEXPS[self._version].match(value) is None:
            raise HTTPException(
                status_code=self._error_status_code,
                detail=f"The provided value is not a valid uuid (version {self._version})",
            )

        return value
