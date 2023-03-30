# coding=utf-8
from pathlib import Path

from binance_data_collector.api import FactoryProvider, Module

from binance_data_collector.environments import environment

from .app_controller import AppController
from .app_service import AppService
from .constants import REPOSITORY_TOKEN
from .helpers.currency_pair_manager import CurrencyPairManager
from .helpers.data_collector import DataCollector
from .helpers.data_file_manager import DataFileManager
from .helpers.web_socket_manager import WebSocketManager
from .models.currency_pair import CurrencyPair
from .models.file_mock_repository import FileMockRepository


def create_repository() -> FileMockRepository:
    fmr: FileMockRepository[CurrencyPair] = FileMockRepository[CurrencyPair](
        path=Path(environment.data_root) / "currency_pairs.json",
    )

    fmr.load()

    return fmr


@Module(
    controllers=[AppController],
    providers=[
        FactoryProvider(
            provide=REPOSITORY_TOKEN,
            use_factory=create_repository,
        ),
        WebSocketManager,
        DataFileManager,
        DataCollector,
        CurrencyPairManager,
        AppService,
    ],
)
class AppModule(object):
    pass
