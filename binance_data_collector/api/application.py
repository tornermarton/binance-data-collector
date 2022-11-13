# coding=utf-8
__all__ = ["Application"]

import inspect
import logging
import typing

import fastapi
import uvicorn

from binance_data_collector.api.constants import (
    API_METADATA_KEY,
    CONTROLLER_METADATA_KEY,
    HTTP_ENDPOINT_METADATA_KEY,
    INJECTABLE_METADATA_KEY,
    MODULE_METADATA_KEY,
)
from .controller import ControllerMetadata
from .http import HTTPEndpointMetadata
from .injectable import InjectableMetadata
from .injection import ClassProvider, FactoryProvider, Inject, ValueProvider
from .lifecycle import OnDestroy, OnInit
from .module import ModuleMetadata
from .types import InjectionToken, ModuleLike


KT: typing.TypeVar = typing.TypeVar("KT")


class Application(object):
    def __init__(self, module: ...) -> None:
        self._app: fastapi.FastAPI = fastapi.FastAPI()

        self._providers: dict[InjectionToken, typing.Any] = self.create_providers(
            module_class=module,
        )
        self._controllers: dict[typing.Any, typing.Any] = self.create_controllers(
            module_class=module,
            providers=self._providers,
        )

        for controller in self._controllers.values():
            self.register_endpoints(
                controller=controller,
                base_path_segments=[]
            )

    def init_components(self, components: list[typing.Any]) -> None:
        for component in components:
            if isinstance(component, OnInit):
                component.on_init()

    def destroy_components(self, components: list[typing.Any]) -> None:
        for component in components:
            if isinstance(component, OnDestroy):
                component.on_destroy()

    def listen(self, port: int = 3000) -> None:
        self.init_components(components=list(self._providers.values()))
        self.init_components(components=list(self._controllers.values()))

        uvicorn.run(
            app=self._app,
            host="0.0.0.0",
            port=port,
            log_level=logging.INFO,
            log_config=None,
        )

        self.destroy_components(components=list(self._controllers.values()))
        self.destroy_components(components=list(self._providers.values()))

    def get_api_metadata(self, o: typing.Any, key: str) -> typing.Any:
        metadata: dict[str, typing.Any] = getattr(o, API_METADATA_KEY)

        return metadata.get(key)

    def get_dependencies(
        self,
        method: typing.Callable,
        providers: dict[InjectionToken, typing.Any],
    ) -> dict[str, typing.Any]:
        dependencies: dict[str, typing.Any] = {}

        for signature in inspect.signature(method).parameters.values():
            if signature.name == "self":
                continue

            if isinstance(signature.default, Inject):
                token: InjectionToken = signature.default.token
            else:
                try:
                    token: typing.Type = signature.annotation.__name__
                except AttributeError:
                    # Support `from __future__ import annotations`
                    # https://docs.python.org/3/library/inspect.html#inspect.signature
                    token: typing.Type = signature.annotation

            if token not in providers:
                raise RuntimeError(f"Provider not found for {token}")

            dependencies[signature.name] = providers[token]

        return dependencies

    def instantiate_with_providers(
        self,
        class_: typing.Type,
        providers: dict[InjectionToken, typing.Any],
    ) -> typing.Any:
        dependencies: dict[str, typing.Any] = self.get_dependencies(
            method=class_.__init__,
            providers=providers
        )

        return class_(**dependencies)

    def create_providers(
        self,
        module_class: ModuleLike,
    ) -> dict[InjectionToken, typing.Any]:
        providers: dict[InjectionToken, typing.Any] = {}

        module_metadata: ModuleMetadata = self.get_api_metadata(
            o=module_class,
            key=MODULE_METADATA_KEY,
        )

        for provider in module_metadata.providers:
            if (
                    isinstance(provider, ValueProvider)
                    or
                    isinstance(provider, ClassProvider)
                    or
                    isinstance(provider, FactoryProvider)
            ):
                providers[provider.provide] = provider.get_value()
            else:
                metadata: InjectableMetadata = self.get_api_metadata(
                    o=provider,
                    key=INJECTABLE_METADATA_KEY,
                )

                provider: typing.Any = self.instantiate_with_providers(
                    class_=provider,
                    providers=providers,
                )
                providers[provider.__class__.__name__] = provider

        return providers

    def get_endpoints(
        self,
        controller: typing.Any
    ) -> list[tuple[typing.Callable, HTTPEndpointMetadata]]:
        members: list[tuple[str, typing.Callable]] = inspect.getmembers(
            object=controller,
            predicate=inspect.ismethod
        )

        endpoints: list[tuple[typing.Callable, HTTPEndpointMetadata]] = []
        for _, method in members:
            try:
                metadata: HTTPEndpointMetadata = self.get_api_metadata(
                    o=method,
                    key=HTTP_ENDPOINT_METADATA_KEY,
                )

                endpoints.append((method, metadata))
            except AttributeError:
                # No metadata is found for method, it is not an API endpoint
                pass

        endpoints = list(reversed(endpoints))

        return endpoints

    def register_endpoints(
        self,
        controller: typing.Any,
        base_path_segments: list[str],
    ) -> None:
        controller_metadata: ControllerMetadata = self.get_api_metadata(
            o=controller.__class__,
            key=CONTROLLER_METADATA_KEY,
        )

        controller_path_segments: list[str] = base_path_segments.copy()

        if controller_metadata.path != "/" and controller_metadata.path != "":
            controller_path_segments.append(controller_metadata.path)

        for method, metadata in self.get_endpoints(controller=controller):
            path_segments: list[str] = controller_path_segments.copy()

            endpoint_path: str = metadata.path
            if endpoint_path is not None and endpoint_path != "":
                path_segments.append(endpoint_path)

            self._app.router.add_api_route(
                path='/' + '/'.join(path_segments),
                endpoint=method,
                response_model=inspect.signature(method).return_annotation,
                status_code=metadata.status_code,
                tags=controller_path_segments,
                methods=[metadata.method.name],
            )

    def create_controllers(
        self,
        module_class: ModuleLike,
        providers: dict[InjectionToken, typing.Any],
    ) -> dict[typing.Any, typing.Any]:
        controllers: dict[typing.Any, typing.Any] = {}

        module_metadata: ModuleMetadata = self.get_api_metadata(
            o=module_class,
            key=MODULE_METADATA_KEY,
        )

        for controller_class in module_metadata.controllers:
            metadata: ControllerMetadata = self.get_api_metadata(
                o=controller_class,
                key=CONTROLLER_METADATA_KEY,
            )

            controller: typing.Any = self.instantiate_with_providers(
                class_=controller_class,
                providers=providers,
            )
            controllers[controller_class] = controller

        return controllers
