# coding=utf-8
__all__ = [
    "JsonFormatter"
]

import datetime
import io
import logging
import traceback
from types import TracebackType
from typing import Optional, Any, Callable, Union, Type

try:
    import jsons as json
except ImportError:
    import json


class JsonFormatter(logging.Formatter):
    """Format log records as JSON"""

    formatter: Callable[[dict], str] = json.dumps

    def __init__(
        self,
        fields: list[str],
        rename_fields: Optional[dict[str, str]] = None,
        static_fields: Optional[dict[str, Any]] = None,
        timestamp: bool = True,
        dt_fmt: Optional[str] = None,
        dt_tz: datetime.tzinfo = datetime.timezone.utc,
    ) -> None:
        """Initialize the created instance"""

        super().__init__()

        self._fields: list[str] = fields
        self._rename_fields: Optional[dict[str, str]] = rename_fields or {}
        self._static_fields: Optional[dict[str, Any]] = static_fields or {}
        self._dt_fmt: Optional[str] = dt_fmt
        self._dt_tz: datetime.tzinfo = dt_tz

        self._uses_time: bool = False

        if "asctime" in self._fields:
            self._uses_time = True
        elif timestamp:
            # Append to the beginning
            self._fields = ["asctime"] + self._fields
            self._rename_fields["asctime"] = "@timestamp"

            self._uses_time = True

    def format_exception(
        self,
        exc_info: Union[tuple[Type[BaseException], BaseException, Optional[TracebackType]], tuple[None, None, None]]  # noqa
    ) -> str:
        """Format the provided exception as a single line"""

        sio: io.StringIO = io.StringIO()
        traceback.print_exception(*exc_info, None, sio)
        s: str = sio.getvalue()
        sio.close()

        if s[-1:] == '\n':
            s = s[:-1]

        return s

    def format_stack(self, stack_info: str) -> str:
        """Format the provided stack info"""

        return stack_info

    def format_time(self, dt: datetime.datetime) -> str:
        """Convert datetime to string, default ISO standard"""

        if self._dt_fmt is None:
            return dt.isoformat()

        return dt.strftime(self._dt_fmt)

    def format(self, record: logging.LogRecord) -> str:
        """Format the provided LogRecord as string, omit None values"""

        log_dict: dict[str, Any] = {}

        # This replaces args in message with user supplied args (not recommended but supported)
        record.message = record.getMessage()

        if self._uses_time:
            dt: datetime.datetime = datetime.datetime.fromtimestamp(
                record.created,
                tz=self._dt_tz
            )
            record.asctime = self.format_time(dt=dt)

        if record.exc_info:
            record.exc_info = self.format_exception(exc_info=record.exc_info)
        elif record.exc_text:
            record.exc_info = record.exc_text

        if record.stack_info:
            record.stack_info = self.format_stack(record.stack_info)

        for field in self._fields:
            value: Any = record.__dict__.get(field)

            if value is not None:
                # key is either field itself (default) or the rename variant
                log_dict[self._rename_fields.get(field, field)] = value

        return JsonFormatter.formatter({**log_dict, **self._static_fields})


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    logger: logging.Logger = logging.getLogger()
    logger.handlers[0].setFormatter(
        JsonFormatter(
            fields=["name", "message", "exc_info"],
            rename_fields={"name": "log.logger"},
            static_fields={"static_field": "static value"}
        )
    )

    logger.info("Example info")

    try:
        raise ValueError("Example exception")
    except Exception as e:
        logger.error(e, exc_info=e)
        logger.exception(e)  # No need for exc_info
        logger.critical(e, exc_info=e)
