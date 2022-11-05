# coding=utf-8
import dataclasses
import typing

from .constants import CONTROLLER_METADATA_KEY
from .core import ApiDecorator, ApiMetadata, ApiMetadataDescriptor
from .types import ControllerLike


@dataclasses.dataclass(frozen=True)
class ControllerMetadata(ApiMetadata):
    path: str


class Controller(ApiDecorator[typing.Type, ControllerLike, ControllerMetadata]):
    def __init__(self, path: str) -> None:
        self._path: str = path

    def create_api_metadata(self) -> ApiMetadataDescriptor[ControllerMetadata]:
        return ApiMetadataDescriptor(
            key=CONTROLLER_METADATA_KEY,
            metadata=ControllerMetadata(
                path=self._path,
            ),
        )
