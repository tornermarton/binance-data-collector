# coding=utf-8
import abc
import typing

from .constants import API_METADATA_KEY

T = typing.TypeVar("T", bound=type)
R = typing.TypeVar("R", bound=type)


class ApiMetadata(object):
    pass


M = typing.TypeVar("M", bound=ApiMetadata)


class ApiMetadataDescriptor(typing.Generic[M]):
    def __init__(self, key: str, metadata: M) -> None:
        self._key: str = key
        self._metadata: M = metadata

    @property
    def key(self) -> str:
        return self._key

    @property
    def metadata(self) -> M:
        return self._metadata


class ApiDecorator(typing.Generic[T, R, M], metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def create_api_metadata(self) -> ApiMetadataDescriptor[M]:
        raise NotImplementedError()

    def __call__(self, o: T) -> R:
        descriptor: ApiMetadataDescriptor[M] = self.create_api_metadata()

        api_metadata: dict[str, ApiMetadata] = getattr(o, API_METADATA_KEY, {})
        api_metadata[descriptor.key] = descriptor.metadata

        setattr(o, API_METADATA_KEY, api_metadata)

        return o