# coding=utf-8
import dataclasses
import typing

from .constants import MODULE_METADATA_KEY
from .core import ApiDecorator, ApiMetadata, ApiMetadataDescriptor, T
from .injection import ProviderLike
from .types import ControllerLike, ModuleLike


@dataclasses.dataclass(frozen=True)
class ModuleMetadata(ApiMetadata):
    imports: list[ModuleLike]
    controllers: list[ControllerLike]
    providers: list[ProviderLike]
    exports: list[ModuleLike | ProviderLike]


class Module(ApiDecorator[T, ModuleLike, ModuleMetadata]):
    def __init__(
        self,
        imports: list[ModuleLike] | None = None,
        controllers: list[ControllerLike] | None = None,
        providers: list[ProviderLike] | None = None,
        exports: list[ModuleLike | ProviderLike] | None = None,
    ) -> None:
        self._imports: list[ModuleLike] = imports or []
        self._controllers: list[ControllerLike] = controllers or []
        self._providers: list[ProviderLike] = providers or []
        self._exports: list[ModuleLike | ProviderLike] = exports or []

    def create_api_metadata(self) -> ApiMetadataDescriptor[ModuleMetadata]:
        return ApiMetadataDescriptor(
            key=MODULE_METADATA_KEY,
            metadata=ModuleMetadata(
                imports=self._imports,
                controllers=self._controllers,
                providers=self._providers,
                exports=self._exports,
            ),
        )
