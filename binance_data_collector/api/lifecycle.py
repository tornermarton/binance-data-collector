# coding=utf-8
import abc


class OnInit(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def on_init(self) -> None:
        raise NotImplementedError()


class OnDestroy(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def on_destroy(self) -> None:
        raise NotImplementedError()
