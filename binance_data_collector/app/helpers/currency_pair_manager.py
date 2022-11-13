# coding=utf-8
__all__ = ["CurrencyPairManager"]

import threading
import time
import typing

import requests

from binance_data_collector.api import Injectable
from binance_data_collector.api.lifecycle import OnDestroy, OnInit
from binance_data_collector.rxpy import Observable, Subject

from binance_data_collector.app.models.currency_pair import CurrencyPair
from binance_data_collector.app.models.currency_pair_change import CurrencyPairChange
from binance_data_collector.app.utils import LoggingMixin


@Injectable()
class CurrencyPairManager(threading.Thread, LoggingMixin, OnInit, OnDestroy):
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

        self.log.info(f"Updating currency pairs, changes: {change}")

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
            self.log.exception("Could not update currency pairs", exc_info=e)

    def run(self) -> None:
        counter: int = 0

        while not self._stopped:
            if counter <= 0:
                self._update()

                counter = (5 * 60)

            counter -= 5
            time.sleep(5)

    def on_init(self) -> None:
        self.start()

    def on_destroy(self) -> None:
        self._stopped = True
        self.join()
