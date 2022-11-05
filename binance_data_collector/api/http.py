# coding=utf-8
import dataclasses
import enum
import typing

from .constants import HTTP_ENDPOINT_METADATA_KEY
from .core import ApiDecorator, ApiMetadata, ApiMetadataDescriptor


class HTTPRequestMethod(enum.Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


@dataclasses.dataclass(frozen=True)
class HTTPEndpointMetadata(ApiMetadata):
    method: HTTPRequestMethod
    path: str
    status_code: int


class HTTPEndpoint(
    ApiDecorator[typing.Callable, typing.Callable, HTTPEndpointMetadata]
):
    def __init__(
        self,
        method: HTTPRequestMethod,
        path: str | None = None,
        status_code: int = 200,
    ) -> None:
        self._method: HTTPRequestMethod = method
        self._path: str | None = path
        self._code: int = status_code

    def create_api_metadata(
        self,
    ) -> ApiMetadataDescriptor[HTTPEndpointMetadata]:
        return ApiMetadataDescriptor(
            key=HTTP_ENDPOINT_METADATA_KEY,
            metadata=HTTPEndpointMetadata(
                method=self._method,
                path=self._path,
                status_code=self._code,
            ),
        )


class Get(HTTPEndpoint):
    def __init__(
        self,
        path: str | None = None,
        status_code: int = 200,
    ) -> None:
        super().__init__(HTTPRequestMethod.GET, path, status_code)


class Post(HTTPEndpoint):
    def __init__(
        self,
        path: str | None = None,
        status_code: int = 201,
    ) -> None:
        super().__init__(HTTPRequestMethod.POST, path, status_code)


class Put(HTTPEndpoint):
    def __init__(
        self,
        path: str | None = None,
        status_code: int = 200,
    ) -> None:
        super().__init__(HTTPRequestMethod.PUT, path, status_code)


class Patch(HTTPEndpoint):
    def __init__(
        self,
        path: str | None = None,
        status_code: int = 200,
    ) -> None:
        super().__init__(HTTPRequestMethod.PATCH, path, status_code)


class Delete(HTTPEndpoint):
    def __init__(
        self,
        path: str | None = None,
        status_code: int = 204,
    ) -> None:
        super().__init__(HTTPRequestMethod.DELETE, path, status_code)
