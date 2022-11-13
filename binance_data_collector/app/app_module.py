# coding=utf-8
from pathlib import Path

from binance_data_collector.api import Module
from binance_data_collector.api.config import Config

from .app_controller import AppController
from .app_service import AppService
from .helpers.currency_pair_manager import CurrencyPairManager
from .helpers.data_collector import DataCollector
from .helpers.data_file_manager import DataFileManager
from .helpers.web_socket_manager import WebSocketManager


@Module(
    controllers=[AppController],
    providers=[
        Config.for_root(
            path=Path(__file__).parent.parent / "config" / "config.yaml",
        ),
        CurrencyPairManager,
        DataFileManager,
        WebSocketManager,
        DataCollector,
        AppService,
    ],
)
class AppModule(object):
    pass
