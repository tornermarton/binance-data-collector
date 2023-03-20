# coding=utf-8
__all__ = [
    "HttpStatus",
    "HttpEndpointMetadata",
    "Get",
    "Post",
    "Put",
    "Patch",
    "Delete",
]

import dataclasses
import enum
import typing

from .constants import HTTP_ENDPOINT_METADATA_KEY
from .core import ApiDecorator, ApiMetadata, ApiMetadataDescriptor


class HttpRequestMethod(enum.Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class HttpStatus(enum.IntEnum):
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204

    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404


@dataclasses.dataclass(frozen=True)
class HttpEndpointMetadata(ApiMetadata):
    method: HttpRequestMethod
    path: str
    status_code: int
    tags: list[str]


class HttpEndpoint(
    ApiDecorator[typing.Callable, typing.Callable, HttpEndpointMetadata]
):
    def __init__(
        self,
        method: HttpRequestMethod,
        path: str | None = None,
        status_code: int = HttpStatus.OK,
        tags: list[str] | None = None,
    ) -> None:
        self._method: HttpRequestMethod = method
        self._path: str | None = path
        self._code: int = status_code
        self._tags: list[str] = tags or []

    def create_api_metadata(
        self,
    ) -> ApiMetadataDescriptor[HttpEndpointMetadata]:
        return ApiMetadataDescriptor(
            key=HTTP_ENDPOINT_METADATA_KEY,
            metadata=HttpEndpointMetadata(
                method=self._method,
                path=self._path,
                status_code=self._code,
                tags=self._tags,
            ),
        )


class Get(HttpEndpoint):
    def __init__(
        self,
        path: str | None = None,
        status_code: int = HttpStatus.OK,
        tags: list[str] | None = None,
    ) -> None:
        super().__init__(HttpRequestMethod.GET, path, status_code, tags)


class Post(HttpEndpoint):
    def __init__(
        self,
        path: str | None = None,
        status_code: int = HttpStatus.CREATED,
        tags: list[str] | None = None,
    ) -> None:
        super().__init__(HttpRequestMethod.POST, path, status_code, tags)


class Put(HttpEndpoint):
    def __init__(
        self,
        path: str | None = None,
        status_code: int = HttpStatus.OK,
        tags: list[str] | None = None,
    ) -> None:
        super().__init__(HttpRequestMethod.PUT, path, status_code, tags)


class Patch(HttpEndpoint):
    def __init__(
        self,
        path: str | None = None,
        status_code: int = HttpStatus.OK,
        tags: list[str] | None = None,
    ) -> None:
        super().__init__(HttpRequestMethod.PATCH, path, status_code, tags)


class Delete(HttpEndpoint):
    def __init__(
        self,
        path: str | None = None,
        status_code: int = HttpStatus.ACCEPTED,
        tags: list[str] | None = None,
    ) -> None:
        super().__init__(HttpRequestMethod.DELETE, path, status_code, tags)
