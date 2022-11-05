# coding=utf-8
from binance_data_collector.api import Module

from .app_controller import AppController
from .app_service import AppService


class A:
    pass


@Module(controllers=["asd"])
def asd():
    ...


@Module(
    controllers=[AppController, "asd"],
    providers=[AppService],
)
class AppModule(object):
    pass


print(type(AppModule))
