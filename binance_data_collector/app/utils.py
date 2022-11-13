# coding=utf-8
import logging


class LoggingMixin:
    _logger: logging.Logger | None = None

    @property
    def log(self) -> logging.Logger:
        """Returns a logger."""

        if self._logger is None:
            self._logger = logging.getLogger(
                name=self.__class__.__module__ + "." + self.__class__.__name__,
            )

        return self._logger
