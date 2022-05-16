# coding=utf-8
__all__ = ["WebSocketClientProtocol", "WebSocketClientFactory"]

import datetime
import logging
from pathlib import Path
from typing import Any

try:
    import ujson as json
except ImportError:
    import json

from autobahn.twisted import websocket
from twisted.internet import protocol

from binance_data_collector.currency_pair import CurrencyPair


class WebSocketClientProtocol(websocket.WebSocketClientProtocol):
    def connectionMade(self) -> None:
        super().connectionMade()

        try:
            self.transport.setTcpKeepAlive(1)
        except AttributeError:
            print("AttributeError silenced")

    def onOpen(self) -> None:
        super().onOpen()

        logging.info("WebSocket connection opened!")

        # reset the delay after reconnecting
        self.factory.resetDelay()

    def onMessage(self, payload: bytes, isBinary: bool) -> None:
        if not isBinary:
            try:
                message: dict[str, Any] = json.loads(payload.decode("utf-8"))

                logging.debug(f"Message received: {message}")

                if "stream" in message:
                    symbol, channel, *_ = message["stream"].split('@')

                    path: Path = Path(
                        self.factory.buffers_root,
                        self.factory.currency_pairs[symbol],
                        f"{channel}_{datetime.date.today()}.json"
                    )

                    path.parent.mkdir(parents=True, exist_ok=True)

                    with path.open(mode='ab') as file:
                        file.write(payload)
                        file.write(b'\n')

                    logging.debug("Message saved.")
                else:
                    logging.warning(f"Unexpected message: {message}")
            except Exception as e:
                logging.exception(f"Could not process payload.", exc_info=e)


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
        buffers_root: Path,
        currency_pairs: list[CurrencyPair],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.setProtocolOptions(autoPingInterval=300, autoPingTimeout=30)

        self.buffers_root: Path = buffers_root
        self.currency_pairs: dict[str, str] = {
            c.symbol: c.lower() for c in currency_pairs
        }
