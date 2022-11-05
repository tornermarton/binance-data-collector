# coding=utf-8
import datetime
import logging
import threading
import time
import typing

import requests

from binance_data_collector.api import Injectable
from binance_data_collector.common import Observable, Observer, Subject

from .constants import TZ
from .models.currency_pair import CurrencyPair
from .models.currency_pair_change import CurrencyPairChange


class CurrencyPairManager(threading.Thread):
    def __init__(self) -> None:
        super().__init__()

        self._currency_pairs: Subject[set[CurrencyPair]] = Subject(value=set())

        self._changes: Subject[CurrencyPairChange] = Subject()

        self._stopped: bool = False

    @property
    def currency_pairs(self) -> Observable[set[CurrencyPair]]:
        return self._currency_pairs

    @property
    def changes(self) -> Observable[CurrencyPairChange]:
        return self._changes.as_observable()

    def _update_currency_pairs(
        self,
        new_currency_pairs: set[CurrencyPair],
    ) -> None:
        old_currency_pairs: set[CurrencyPair] = self._currency_pairs.value or {}

        change: CurrencyPairChange = CurrencyPairChange(
            added={
                cp for cp in new_currency_pairs if cp not in old_currency_pairs
            },
            removed={
                cp for cp in old_currency_pairs if cp not in new_currency_pairs
            },
        )

        logging.info(f"Updating currency pairs, changes: {change}")

        self._currency_pairs.next(value=new_currency_pairs)
        self._changes.next(value=change)

    def _update(self) -> None:
        try:
            response: requests.Response = requests.get(
                "https://api.binance.com/api/v3/exchangeInfo"
            )
            content: dict[str, typing.Any] = response.json()

            self._update_currency_pairs(
                new_currency_pairs={
                    CurrencyPair(
                        base=symbol["baseAsset"],
                        quote=symbol["quoteAsset"],
                    )
                    for symbol in content["symbols"]
                },
            )
        except Exception as e:
            logging.exception("Could not update currency pairs", exc_info=e)

    def run(self) -> None:
        counter: int = 0

        while not self._stopped:
            if counter <= 0:
                self._update()

                counter = (5 * 60)

            counter -= 5
            time.sleep(5)

    def stop(self) -> None:
        self._stopped = True


@Injectable()
class AppService(object):
    def __init__(self) -> None:
        self._currency_pairs: dict[str, CurrencyPair] = {}
        self._last_change: typing.Optional[CurrencyPairChange] = None
        self._last_update_dt: typing.Optional[datetime.datetime] = None
        self._last_change_dt: typing.Optional[datetime.datetime] = None

        self._lock: threading.Lock = threading.Lock()

        manager: CurrencyPairManager = CurrencyPairManager()
        manager.start()
        manager.currency_pairs.subscribe(
            observer=Observer(
                next=self._update_currency_pairs,
            ),
        )
        manager.changes.subscribe(
            observer=Observer(
                next=self._handle_currency_pair_change,
            ),
        )

    def _update_currency_pairs(self, currency_pairs: set[CurrencyPair]) -> None:
        with self._lock:
            self._currency_pairs = {cp.symbol: cp for cp in currency_pairs}
            self._last_update_dt = datetime.datetime.now(tz=TZ)

    def get_last_update_dt(self) -> typing.Optional[datetime.datetime]:
        return self._last_update_dt

    def _handle_currency_pair_change(self, change: CurrencyPairChange) -> None:
        self._last_change = change
        self._last_change_dt = datetime.datetime.now(tz=TZ)

    def get_last_change(self) -> CurrencyPairChange:
        return self._last_change

    def get_last_change_dt(self) -> typing.Optional[datetime.datetime]:
        return self._last_change_dt

    def get_currency_pairs(self) -> list[CurrencyPair]:
        with self._lock:
            return list(self._currency_pairs.values())

    def get_currency_pair(self, symbol: str) -> CurrencyPair:
        with self._lock:
            return self._currency_pairs.get(symbol, None)
