# coding=utf-8
__all__ = ["BinanceStreamDataCollector", "BinanceSnapshotDataCollector"]

import abc
import dataclasses
import logging
from typing import Any

try:
    import ujson as json
except ImportError:
    import json

import requests
from autobahn.twisted import websocket
from twisted.internet import reactor

from binance_data_collector.app.models.currency_pair import CurrencyPair
from binance_data_collector_old.data_file_manager import DataFileManager
from binance_data_collector_old.websockets import WebSocketClientFactory


class BinanceDataCollector(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def run(self) -> None:
        raise NotImplementedError()


@dataclasses.dataclass(frozen=True)
class BinanceStreamDataCollector(BinanceDataCollector):
    data_file_manager: DataFileManager
    channel: str
    currency_pairs: list[CurrencyPair]

    def run(self) -> None:
        streams: str = '/'.join(
            [f"{c.symbol}@{self.channel}" for c in self.currency_pairs]
        )

        websocket.connectWS(
            factory=WebSocketClientFactory(
                data_file_manager=self.data_file_manager,
                currency_pairs=self.currency_pairs,
                url=f"wss://stream.binance.com:9443/stream?streams={streams}",
            )
        )
        reactor.run()

    def stop(self) -> None:
        reactor.stop()


@dataclasses.dataclass(frozen=True)
class BinanceSnapshotDataCollector(BinanceDataCollector):
    data_file_manager: DataFileManager
    depth: int
    currency_pairs: list[CurrencyPair]

    def _process_currency_pair(self, currency_pair: CurrencyPair) -> None:
        symbol: str = currency_pair.upper('')
        query: str = f"symbol={symbol}&limit={self.depth}"

        response: requests.Response = requests.get(
            f"https://www.binance.com/api/v3/depth?{query}"
        )

        payload: bytes = response.content
        snapshot: dict[str, Any] = json.loads(
            payload.decode(encoding=response.encoding)
        )

        logging.debug(f"Snapshot collected: {snapshot}")

        if "lastUpdateId" in snapshot:
            self.data_file_manager.get_file(
                currency_pair=currency_pair,
            ).write_data(
                data=snapshot,
            )

            logging.debug(f"Snapshot saved: {snapshot}")
        else:
            raise RuntimeError(f"Unexpected snapshot: {snapshot}")

    def run(self) -> None:
        logging.info("Start collecting snapshots...")

        for currency_pair in self.currency_pairs:
            try:
                self._process_currency_pair(currency_pair=currency_pair)
            except Exception as e:
                logging.exception(e)

        logging.info("Snapshots collected.")

    def stop(self) -> None:
        reactor.stop()
