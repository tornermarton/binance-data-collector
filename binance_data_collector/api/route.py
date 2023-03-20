# coding=utf-8
__all__ = ["Request", "Query", "Param", "Body"]

from binance_data_collector.api.pipes import PipeTransform


class Request(object):
    pass


class Query(object):
    def __init__(self, *pipes: PipeTransform) -> None:
        self.pipes: list[PipeTransform] = list(pipes)


class Param(object):
    def __init__(self, name: str, *pipes: PipeTransform) -> None:
        self.name: str = name
        self.pipes: list[PipeTransform] = list(pipes)


class Body(object):
    def __init__(self, *pipes: PipeTransform) -> None:
        self.pipes: list[PipeTransform] = list(pipes)
