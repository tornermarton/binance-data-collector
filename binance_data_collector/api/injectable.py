# coding=utf-8
import dataclasses
import typing

from .constants import INJECTABLE_METADATA_KEY
from .core import ApiDecorator, ApiMetadata, ApiMetadataDescriptor
from .injection import ProviderLike


@dataclasses.dataclass(frozen=True)
class InjectableMetadata(ApiMetadata):
    pass


class Injectable(ApiDecorator[typing.Type, ProviderLike, InjectableMetadata]):
    def create_api_metadata(self):
        return ApiMetadataDescriptor(
            key=INJECTABLE_METADATA_KEY,
            metadata=InjectableMetadata(),
        )
