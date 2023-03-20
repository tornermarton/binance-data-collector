# coding=utf-8
__all__ = ["LoggingMixin", "JsonLoggingFormatter"]

import datetime
import io
import logging
import traceback
import types
import typing

try:
    import ujson as json
except ImportError:
    import json


ExceptionInfo: typing.TypeAlias = typing.Union[
    typing.Tuple[
        typing.Type[BaseException],
        BaseException,
        typing.Optional[types.TracebackType],
    ],
    typing.Tuple[None, None, None],
]


def get_logger_for(cls: typing.Type) -> logging.Logger:
    """Create a logger for the passed class"""

    return logging.getLogger(name=cls.__module__ + "." + cls.__name__)


class LoggingMixin:
    _logger: typing.Union[logging.Logger, None] = None

    @property
    def log(self) -> logging.Logger:
        """Returns a logger instance which is created on first call"""

        if self._logger is None:
            self._logger = get_logger_for(cls=self.__class__)

        return self._logger


class JsonLoggingFormatter(logging.Formatter):
    """Format log records as JSON"""

    formatter: typing.Callable[[typing.Dict], str] = json.dumps

    def __init__(
        self,
        fields: typing.List[str],
        rename_fields: typing.Optional[typing.Dict[str, str]] = None,
        static_fields: typing.Optional[typing.Dict[str, typing.Any]] = None,
        timestamp: bool = True,
        dt_fmt: typing.Optional[str] = None,
        dt_tz: datetime.tzinfo = datetime.timezone.utc,
    ) -> None:
        """Initialize the created instance"""

        super().__init__()

        self._fields: typing.List[str] = fields
        self._rename_fields: typing.Dict[str, str] = rename_fields or {}
        self._static_fields: typing.Dict[str, typing.Any] = static_fields or {}
        self._dt_fmt: typing.Optional[str] = dt_fmt
        self._dt_tz: datetime.tzinfo = dt_tz

        self._uses_time: bool = False

        if "asctime" in self._fields:
            self._uses_time = True
        elif timestamp:
            # Append to the beginning
            self._fields = ["asctime"] + self._fields
            self._rename_fields["asctime"] = "@timestamp"

            self._uses_time = True

    def format_exception(self, exc_info: ExceptionInfo) -> str:
        """Format the provided exception as a single line"""

        string_io: io.StringIO = io.StringIO()
        traceback.print_exception(*exc_info, limit=None, file=string_io)
        stack_trace: str = string_io.getvalue()
        string_io.close()

        if stack_trace[-1:] == "\n":
            stack_trace = stack_trace[:-1]

        return stack_trace

    def format_stack(self, stack_info: str) -> str:
        """Format the provided stack info"""

        return stack_info

    def format_time(self, dt: datetime.datetime) -> str:
        """Convert datetime to string, default ISO standard"""

        if self._dt_fmt is None:
            return dt.isoformat()

        return dt.strftime(self._dt_fmt)

    def _prepare_record(self, record: logging.LogRecord) -> logging.LogRecord:
        """Enrich the provided logging.LogRecord with additional information"""

        # This replaces args in message with user supplied args
        # (not recommended but supported)
        record.message = record.getMessage()

        if self._uses_time:
            dt: datetime.datetime = datetime.datetime.fromtimestamp(
                record.created, tz=self._dt_tz
            )
            record.asctime = self.format_time(dt=dt)

        if record.exc_info:
            record.exc_info = self.format_exception(exc_info=record.exc_info)
        elif record.exc_text:
            record.exc_info = record.exc_text

        if record.stack_info:
            record.stack_info = self.format_stack(record.stack_info)

        return record

    def _create_log_dict(
        self,
        record: logging.LogRecord,
    ) -> typing.Dict[str, typing.Any]:
        """Create logged values from the provided logging.LogRecord"""

        log_dict: typing.Dict[str, typing.Any] = {}

        for field in self._fields:
            value: typing.Any = record.__dict__.get(field)

            if value is not None:
                # key is either field itself (default) or the renamed variant
                key: str = self._rename_fields.get(field, field)
                log_dict[key] = value

        return {**log_dict, **self._static_fields}

    def format(self, record: logging.LogRecord) -> str:
        """Format the provided logging.LogRecord as string, omit None values"""

        record = self._prepare_record(record=record)

        log_dict: typing.Dict[str, typing.Any] = \
            self._create_log_dict(record=record)

        return JsonLoggingFormatter.formatter(log_dict)
