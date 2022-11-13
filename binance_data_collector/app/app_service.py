# coding=utf-8
import datetime
import threading
import typing

from fastapi import HTTPException

from binance_data_collector.api import Injectable
from binance_data_collector.api.lifecycle import OnDestroy, OnInit
from binance_data_collector.rxpy import Observer, Subscription

from .constants import TZ
from .helpers.currency_pair_manager import CurrencyPairManager
from .helpers.data_collector import DataCollector
from .models.currency_pair import CurrencyPair
from .models.currency_pair_change import CurrencyPairChange


@Injectable()
class AppService(OnInit, OnDestroy):
    def __init__(
        self,
        currency_pair_manager: CurrencyPairManager,
        data_collector: DataCollector,
    ) -> None:
        self._currency_pair_manager: CurrencyPairManager = currency_pair_manager
        self._data_collector: DataCollector = data_collector

        self._currency_pairs: dict[str, CurrencyPair] = {}

        self._last_update_dt: typing.Optional[datetime.datetime] = None
        self._last_change_dt: typing.Optional[datetime.datetime] = None
        self._last_change: typing.Optional[CurrencyPairChange] = None

        self._lock: threading.Lock = threading.Lock()

        self._subscriptions: list[Subscription] = []

    def _update_currency_pairs(self, currency_pairs: set[CurrencyPair]) -> None:
        with self._lock:
            self._currency_pairs = {cp.symbol: cp for cp in currency_pairs}
            self._last_update_dt = datetime.datetime.now(tz=TZ)

    def _handle_currency_pair_change(self, change: CurrencyPairChange) -> None:
        self._last_change = change
        self._last_change_dt = datetime.datetime.now(tz=TZ)

        with self._lock:
            for removed in change.removed:
                if self.is_active(currency_pair=removed):
                    self._data_collector.remove_currency_pair(
                        currency_pair=removed,
                    )

    def is_active(self, currency_pair: CurrencyPair) -> bool:
        return self._data_collector.is_collecting(currency_pair=currency_pair)

    def get_last_update_dt(self) -> typing.Optional[datetime.datetime]:
        return self._last_update_dt

    def get_last_change_dt(self) -> typing.Optional[datetime.datetime]:
        return self._last_change_dt

    def get_last_change(self) -> CurrencyPairChange:
        return self._last_change

    def get_currency_pairs(self) -> list[CurrencyPair]:
        with self._lock:
            return list(self._currency_pairs.values())

    def get_currency_pair(self, symbol: str) -> CurrencyPair:
        with self._lock:
            currency_pair: CurrencyPair | None = self._currency_pairs.get(
                symbol,
                None
            )

            if currency_pair is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"CurrencyPair with symbol [{symbol}] cannot be found",
                )

            return currency_pair

    def activate_currency_pair(self, symbol: str) -> None:
        currency_pair: CurrencyPair = self.get_currency_pair(symbol=symbol)

        self._data_collector.add_currency_pair(currency_pair=currency_pair)

    def deactivate_currency_pair(self, symbol: str) -> None:
        currency_pair: CurrencyPair = self.get_currency_pair(
            symbol=symbol,
        )

        if not self._data_collector.is_collecting(currency_pair=currency_pair):
            raise HTTPException(
                status_code=403,
                detail=f"CurrencyPair with symbol [{symbol}] is not activated",
            )

        self._data_collector.remove_currency_pair(currency_pair=currency_pair)

    def on_init(self) -> None:
        self._subscriptions.append(
            self._currency_pair_manager.currency_pairs.subscribe(
                observer=Observer(
                    next=self._update_currency_pairs,
                ),
            )
        )
        self._subscriptions.append(
            self._currency_pair_manager.changes.subscribe(
                observer=Observer(
                    next=self._handle_currency_pair_change,
                ),
            )
        )

    def on_destroy(self) -> None:
        for subscription in self._subscriptions:
            subscription.unsubscribe()
