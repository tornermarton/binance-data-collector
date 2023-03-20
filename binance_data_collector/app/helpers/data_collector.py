# coding=utf-8
__all__ = ["DataCollector"]

import dataclasses
import datetime
import threading
import typing

import requests

from binance_data_collector.api import Injectable
from binance_data_collector.api.lifecycle import OnDestroy
from binance_data_collector.log import LoggingMixin
from binance_data_collector.rxpy import Subscription

from binance_data_collector.app.models.currency_pair import CurrencyPair

from .data_file_manager import DataFileManager
from .web_socket_manager import (
    WebSocketConnection,
    WebSocketEvent,
    WebSocketEventType,
    WebSocketManager,
    WebSocketMessage
)
from ..constants import TZ

lock: threading.Lock = threading.Lock()


@dataclasses.dataclass()
class CurrencyPairInfo(object):
    value: CurrencyPair
    last_message_dt: datetime.datetime | None = None


@Injectable()
class DataCollector(LoggingMixin, OnDestroy):
    def __init__(
        self,
        data_file_manager: DataFileManager,
        web_socket_manager: WebSocketManager,
    ) -> None:
        self._data_file_manager: DataFileManager = data_file_manager
        self._web_socket_manager: WebSocketManager = web_socket_manager

        self._currency_pairs: dict[str, CurrencyPairInfo] = {}

        self._next_id: int = 1
        self._pending_subscribe: dict[int, CurrencyPair] = {}
        self._pending_unsubscribe: dict[int, CurrencyPair] = {}

        self._connection: typing.Optional[WebSocketConnection] = None

        self._subscriptions: list[Subscription] = []

    @property
    def connected(self) -> bool:
        return self._connection is not None

    def _is_collecting(self, currency_pair: CurrencyPair) -> bool:
        with lock:
            symbol: str = currency_pair.symbol
            return self._currency_pairs.get(symbol, None) is not None

    def _subscribe_symbol(self, symbol: str) -> None:
        self._connection.send_message(
            message={
                "method": "SUBSCRIBE",
                "params":
                    [
                        f"{symbol}@trade",
                        f"{symbol}@depth@100ms"
                    ],
                "id": self._next_id
            }
        )

        self._next_id += 1

    def _unsubscribe_symbol(self, symbol: str) -> None:
        self._connection.send_message(
            message={
                "method": "UNSUBSCRIBE",
                "params":
                    [
                        f"{symbol}@trade",
                        f"{symbol}@depth@100ms"
                    ],
                "id": self._next_id
            }
        )

        self._next_id += 1

    def _resubscribe(self) -> None:
        with lock:
            currency_pairs: list[CurrencyPair] = [
                cp.value for cp in self._currency_pairs.values()
            ]

            for currency_pair in currency_pairs[1:]:
                self._subscribe_symbol(symbol=currency_pair.symbol)

    def _handle_message(self, message: WebSocketMessage) -> None:
        name: str = message.channel.split("@")[0]
        symbol: str = message.symbol

        if self._currency_pairs.get(symbol, None) is None:
            self.log.warning(f"Ignore message for unregistered symbol [{symbol}]")

            return

        currency_pair: CurrencyPair = self._currency_pairs[symbol].value

        self._currency_pairs[symbol].last_message_dt = datetime.datetime.now(tz=TZ)

        try:
            self._data_file_manager.get_file(
                currency_pair=currency_pair,
                name=name,
            ).write_data(
                data=message.data,
            )
        except Exception as e:
            self.log.exception(f"Could not save message [{message}]", exc_info=e)

    def _handle_event(self, event: WebSocketEvent) -> None:
        if event.type == WebSocketEventType.CONNECTED:
            self._resubscribe()
        elif event.type == WebSocketEventType.DISCONNECTED:
            self._disconnect()
        elif event.type == WebSocketEventType.CONTROL_MESSAGE:
            key: int = event.context["id"]

            if key in self._pending_subscribe:
                self._pending_subscribe.pop(key)
            elif key in self._pending_unsubscribe:
                self._pending_unsubscribe.pop(key)

    def _create_subscriptions(self) -> None:
        self._subscriptions.append(
            self._connection.messages.subscribe(on_next=self._handle_message),
        )

        self._subscriptions.append(
            self._connection.events.subscribe(on_next=self._handle_event),
        )

    def _destroy_subscriptions(self) -> None:
        for subscription in self._subscriptions:
            subscription.unsubscribe()

    def _connect_with(self, currency_pair: CurrencyPair) -> None:
        symbol: str = currency_pair.symbol

        query: str = f"streams={symbol}@depth@100ms/{symbol}@trade"
        url: str = f"wss://stream.binance.com:9443/stream?{query}"

        self._connection: WebSocketConnection = \
            self._web_socket_manager.create_connection(url=url)

        self._create_subscriptions()

    def _disconnect(self) -> None:
        self._destroy_subscriptions()

        connection: WebSocketConnection = self._connection
        self._connection = None
        self._web_socket_manager.delete_connection(connection=connection)

    def query_currency_pairs(self) -> list[CurrencyPair]:
        url: str = "https://api.binance.com/api/v3/exchangeInfo"
        response: requests.Response = requests.get(url=url)
        content: dict[str, typing.Any] = response.json()

        return [
            CurrencyPair(base=s["baseAsset"], quote=s["quoteAsset"])
            for s in content["symbols"]
        ]

    def add_currency_pair(self, currency_pair: CurrencyPair) -> None:
        if self._is_collecting(currency_pair=currency_pair):
            return

        self._currency_pairs[currency_pair.symbol] = CurrencyPairInfo(
            value=currency_pair,
        )

        if self.connected:
            with lock:
                self._pending_subscribe[self._next_id] = currency_pair
                self._subscribe_symbol(symbol=currency_pair.symbol)
        else:
            self._connect_with(currency_pair=currency_pair)

    def remove_currency_pair(self, currency_pair: CurrencyPair) -> None:
        if not self._is_collecting(currency_pair=currency_pair):
            return

        self._currency_pairs.pop(currency_pair.symbol)
        self._data_file_manager.close_file(
            currency_pair=currency_pair,
            name="trade",
        )
        self._data_file_manager.close_file(
            currency_pair=currency_pair,
            name="depth",
        )

        if len(self._currency_pairs.keys()) > 1:
            with lock:
                self._pending_unsubscribe[self._next_id] = currency_pair
                self._unsubscribe_symbol(symbol=currency_pair.symbol)
        else:
            self._disconnect()

    def get_last_message_dt_for(
        self,
        currency_pair: CurrencyPair,
    ) -> datetime.datetime | None:
        symbol: str = currency_pair.symbol
        info: CurrencyPairInfo | None = self._currency_pairs.get(symbol, None)

        if info is None:
            return None

        return info.last_message_dt

    def on_destroy(self) -> None:
        if self.connected:
            self._disconnect()
