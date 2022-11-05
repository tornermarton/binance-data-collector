# coding=utf-8
__all__ = ["ExitHandler"]

import signal


class ExitHandler(object):
    _ok: bool = True
    _initialized: bool = False

    @staticmethod
    def _initialize():
        signal.signal(signal.SIGINT, ExitHandler.exit)
        signal.signal(signal.SIGTERM, ExitHandler.exit)

        ExitHandler.initialized = True

    @staticmethod
    def ok() -> bool:
        if not ExitHandler._initialized:
            ExitHandler._initialize()

        return ExitHandler._ok

    @staticmethod
    def exit() -> None:
        ExitHandler._ok = False
