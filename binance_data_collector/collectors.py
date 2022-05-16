# coding=utf-8
__all__ = ["BinanceStreamDataCollector", "BinanceSnapshotDataCollector"]

import abc
import dataclasses
import datetime
import logging
import time
from pathlib import Path

try:
    import ujson as json
except ImportError:
    import json

import requests
from autobahn.twisted import websocket
from twisted.internet import reactor

from binance_data_collector.currency_pair import CurrencyPair
from binance_data_collector.websockets import WebSocketClientFactory


class BinanceDataCollector(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def run(self) -> None:
        raise NotImplementedError()


@dataclasses.dataclass(frozen=True)
class BinanceStreamDataCollector(BinanceDataCollector):
    buffers_root: Path
    channel: str
    currency_pairs: list[CurrencyPair]

    def run(self) -> None:
        streams: str = '/'.join(
            [f"{c.symbol}@{self.channel}" for c in self.currency_pairs]
        )

        websocket.connectWS(
            factory=WebSocketClientFactory(
                buffers_root=self.buffers_root,
                currency_pairs=self.currency_pairs,
                url=f"wss://stream.binance.com:9443/stream?streams={streams}",
            )
        )
        reactor.run()


@dataclasses.dataclass(frozen=True)
class BinanceSnapshotDataCollector(BinanceDataCollector):
    buffers_root: Path
    depth: int
    currency_pairs: list[CurrencyPair]

    def run(self) -> None:
        logging.info("Start collecting snapshots...")

        for c in self.currency_pairs:
            try:
                symbol: str = c.upper('')

                response = requests.get(
                    f"https://www.binance.com/api/v3/depth?symbol={symbol}&limit={self.depth}"
                ).json()

                logging.debug(f"Snapshot collected: {response}")

                if "lastUpdateId" in response:
                    response['time'] = time.time_ns()
                    path: Path = Path(
                        self.buffers_root,
                        c.lower(),
                        f"snapshots_{datetime.date.today()}.json"
                    )

                    path.parent.mkdir(parents=True, exist_ok=True)

                    with path.open(mode='a') as file:
                        file.write(json.dumps(response))
                        file.write('\n')

                    logging.debug("Snapshot saved.")
                else:
                    logging.error(f"Response is not correct: {response}")
            except Exception as e:
                logging.exception(e)

        logging.info("Snapshots collected.")
