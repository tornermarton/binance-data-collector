# coding=utf-8
from binance_data_collector.api.types import ControllerLike

print(type("asd"))

def asd(a: list[ControllerLike] | None = None):
    ...

asd(["asd"])
