# coding=utf-8
__all__ = ["DataCollector"]

import threading

from binance_data_collector.api import Injectable
from binance_data_collector.api.lifecycle import OnDestroy, OnInit
from binance_data_collector.api.config import Config
from binance_data_collector.rxpy import Observer, Subscription

from binance_data_collector.app.models.currency_pair import CurrencyPair
from binance_data_collector.app.utils import LoggingMixin

from .currency_pair_manager import CurrencyPairManager
from .data_file_manager import DataFileManager
from .web_socket_manager import (
    WebSocketConnection,
    WebSocketEvent,
    WebSocketEventType,
    WebSocketManager,
    WebSocketMessage
)

lock: threading.Lock = threading.Lock()


@Injectable()
class DataCollector(LoggingMixin, OnInit, OnDestroy):
    def __init__(
        self,
        config: Config,
        currency_pair_manager: CurrencyPairManager,
        data_file_manager: DataFileManager,
        web_socket_manager: WebSocketManager,
    ) -> None:
        self._currency_pair_manager: CurrencyPairManager = currency_pair_manager
        self._data_file_manager: DataFileManager = data_file_manager
        self._web_socket_manager: WebSocketManager = web_socket_manager

        # only add to this array, do not remove
        self._default_currency_pair: CurrencyPair = CurrencyPair(
            base=config.get("default_currency_pair")["base"],
            quote=config.get("default_currency_pair")["quote"],
        )
        self._currency_pairs: dict[str, CurrencyPair] = {}

        self._next_id: int = 1
        self._pending_subscribe: dict[int, CurrencyPair] = {}
        self._pending_unsubscribe: dict[int, CurrencyPair] = {}

        self._connection: WebSocketConnection | None = None
        self._connected: bool = False

        self._subscriptions: list[Subscription] = []

    @property
    def connected(self) -> bool:
        return self._connection is not None

    def is_collecting(self, currency_pair: CurrencyPair) -> bool:
        with lock:
            return (
                self._currency_pairs.get(currency_pair.symbol, None) is not None
                or
                currency_pair == self._default_currency_pair
            )

    def _check_connection(self) -> None:
        if not self.connected:
            raise RuntimeError("Not connected yet!")

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

    def _resubscribe(self) -> None:
        with lock:
            for currency_pair in self._currency_pairs.values():
                self._subscribe_symbol(symbol=currency_pair.symbol)

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

    def add_currency_pair(self, currency_pair: CurrencyPair) -> None:
        if currency_pair == self._default_currency_pair:
            # always added
            return

        self._check_connection()

        with lock:
            self._pending_subscribe[self._next_id] = currency_pair
            self._subscribe_symbol(symbol=currency_pair.symbol)

    def remove_currency_pair(self, currency_pair: CurrencyPair) -> None:
        if currency_pair == self._default_currency_pair:
            self.log.info("Cannot remove default currency pair!")
            return

        self._check_connection()

        with lock:
            self._pending_unsubscribe[self._next_id] = currency_pair
            self._unsubscribe_symbol(symbol=currency_pair.symbol)

    def handle_message(self, message: WebSocketMessage) -> None:
        if message.symbol == self._default_currency_pair.symbol:
            currency_pair: CurrencyPair = self._default_currency_pair
        else:
            currency_pair: CurrencyPair = self._currency_pairs[message.symbol]

        name: str = message.channel.split("@")[0]

        try:
            self._data_file_manager.get_file(
                currency_pair=currency_pair,
                name=name,
            ).write_data(
                data=message.data,
            )
        except Exception as e:
            self.log.exception(f"Could not save message: {message}", exc_info=e)

    def handle_event(self, event: WebSocketEvent) -> None:
        if event.type == WebSocketEventType.CONNECTED:
            self._resubscribe()

            self._connected = True
        elif event.type == WebSocketEventType.DISCONNECTED:
            self._connected = False
        elif event.type == WebSocketEventType.CONTROL_MESSAGE:
            key: int = event.context["id"]

            if key in self._pending_subscribe:
                currency_pair: CurrencyPair = self._pending_subscribe.pop(key)
                self._currency_pairs[currency_pair.symbol] = currency_pair
            elif key in self._pending_unsubscribe:
                currency_pair: CurrencyPair = self._pending_unsubscribe.pop(key)
                del self._currency_pairs[currency_pair.symbol]
                self._data_file_manager.close_file(
                    currency_pair=currency_pair,
                    name="trade",
                )
                self._data_file_manager.close_file(
                    currency_pair=currency_pair,
                    name="depth",
                )

    def on_init(self) -> None:
        symbol: str = self._default_currency_pair.symbol

        self._connection: WebSocketConnection = self._web_socket_manager.create_connection(
            url=f"wss://stream.binance.com:9443/stream?streams={symbol}@depth@100ms/{symbol}@trade",
        )

        self._subscriptions.append(
            self._connection.messages.subscribe(
                observer=Observer(next=self.handle_message),
            )
        )

        self._subscriptions.append(
            self._connection.events.subscribe(
                observer=Observer(next=self.handle_event),
            )
        )

    def on_destroy(self) -> None:
        for subscription in self._subscriptions:
            subscription.unsubscribe()

        self._web_socket_manager.remove_connection(connection=self._connection)
