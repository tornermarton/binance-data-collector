# coding=utf-8
__all__ = ["WebSocketClientProtocol", "WebSocketClientFactory"]

import logging
from typing import Any

try:
    import ujson as json
except ImportError:
    import json

from autobahn.twisted import websocket
from twisted.internet import protocol
from twisted.internet.interfaces import IAddress

from binance_data_collector.app.models.currency_pair import CurrencyPair
from binance_data_collector_old.data_file_manager import DataFile, DataFileManager


class WebSocketClientProtocol(websocket.WebSocketClientProtocol):
    def __init__(
        self,
        data_file_manager: DataFileManager,
        currency_pairs: list[CurrencyPair],
    ) -> None:
        super().__init__()

        self._data_file_manager: DataFileManager = data_file_manager
        self._currency_pairs: dict[str, CurrencyPair] = {
            c.symbol: c for c in currency_pairs
        }

    def _init_tcp_keepalive(self) -> None:
        try:
            self.transport.setTcpKeepAlive(1)
        except AttributeError:
            logging.warning("AttributeError silenced at TCP keepalive")

    def _process_payload(self, payload: bytes) -> None:
        try:
            message: dict[str, Any] = json.loads(payload.decode("utf-8"))

            logging.debug(f"Message received: {message}")

            if "stream" in message:
                symbol, *_ = message["stream"].split('@')

                data_file: DataFile = self._data_file_manager.get_file(
                    currency_pair=self._currency_pairs[symbol],
                )
                data_file.write_data(data=message)

                logging.debug("Message saved.")
            else:
                logging.warning(f"Unexpected message: {message}")
        except Exception as e:
            logging.exception(f"Could not process payload.", exc_info=e)

    def connectionMade(self) -> None:
        super().connectionMade()

        self._init_tcp_keepalive()

        logging.info("WebSocket connected!")

    def onMessage(self, payload: bytes, isBinary: bool) -> None:
        if not isBinary:
            self._process_payload(payload=payload)


class WebSocketClientFactory(
    websocket.WebSocketClientFactory,
    protocol.ReconnectingClientFactory
):
    initialDelay: float = 0.1
    maxDelay: int = 60
    # None means never stop trying to reconnect
    maxRetries: int = None

    protocol: websocket.WebSocketClientProtocol = WebSocketClientProtocol

    def __init__(
        self,
        data_file_manager: DataFileManager,
        currency_pairs: list[CurrencyPair],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)

        self._data_file_manager: DataFileManager = data_file_manager
        self._currency_pairs: list[CurrencyPair] = currency_pairs

        self.setProtocolOptions(autoPingInterval=300, autoPingTimeout=30)

    def buildProtocol(self, addr: IAddress) -> WebSocketClientProtocol:
        self.resetDelay()

        return WebSocketClientProtocol(
            data_file_manager=self._data_file_manager,
            currency_pairs=self._currency_pairs,
        )
