# coding=utf-8
from __future__ import annotations

__all__ = ["CurrencyPairManager"]

import datetime
import threading
import time

from binance_data_collector.api import Inject, Injectable
from binance_data_collector.api.lifecycle import OnDestroy, OnInit
from binance_data_collector.app.constants import REPOSITORY_TOKEN, TZ
from binance_data_collector.app.helpers.data_collector import DataCollector
from binance_data_collector.app.models.repository import Repository
from binance_data_collector.environments import environment
from binance_data_collector.log import LoggingMixin

from binance_data_collector.app.models.currency_pair import CurrencyPair, CurrencyPairStatus


@Injectable()
class CurrencyPairManager(threading.Thread, LoggingMixin, OnInit, OnDestroy):
    def __init__(
        self,
        data_collector: DataCollector,
        repository: Repository[CurrencyPair] = Inject(token=REPOSITORY_TOKEN),
    ) -> None:
        super().__init__()

        self._data_collector: DataCollector = data_collector
        self._repository: Repository[CurrencyPair] = repository

        # cache currency pairs to prevent constant DB query
        # use symbol dict to allow O(1) lookup
        self._currency_pairs: dict[str, CurrencyPair] = {
            cp.symbol: cp for cp in repository.find()
        }

        active: list[CurrencyPair] = [
            cp for cp in self._currency_pairs.values()
            if (
                cp.status == CurrencyPairStatus.ACTIVE
                or
                cp.status == CurrencyPairStatus.IDLE
            )
        ]

        # resubscribe to all active streams
        for cp in active:
            self._data_collector.add_currency_pair(currency_pair=cp)

        self._stopped: bool = False

    def _is_idle(self, currency_pair: CurrencyPair) -> bool:
        last_message_dt: datetime.datetime = \
            self._data_collector.get_last_message_dt_for(currency_pair=currency_pair)

        threshold: datetime.datetime = \
            datetime.datetime.now(tz=TZ) - datetime.timedelta(minutes=5)

        if last_message_dt is None:
            return False

        return threshold > last_message_dt

    def _refresh(self) -> None:
        try:
            # use symbol dict to allow O(1) lookup
            new_currency_pairs: dict[str, CurrencyPair] = {
                cp.symbol: cp
                for cp in self._data_collector.query_currency_pairs()
            }
        except Exception as e:
            self.log.exception("Could not query currency pairs", exc_info=e)
        else:
            for key, value in self._currency_pairs.items():
                cp: CurrencyPair | None = new_currency_pairs.get(key, None)

                if cp is None:
                    value.status = CurrencyPairStatus.ARCHIVED
                    self._repository.update(uuid=value.uuid, item=value)
                    self._data_collector.remove_currency_pair(
                        currency_pair=value,
                    )
                elif self._is_idle(currency_pair=value):
                    value.status = CurrencyPairStatus.IDLE
                    self._repository.update(uuid=value.uuid, item=value)

            for key, value in new_currency_pairs.items():
                cp: CurrencyPair | None = self._currency_pairs.get(key, None)

                if cp is None:
                    self._repository.create(item=value)
                    self._currency_pairs[key] = value
                elif cp.status == CurrencyPairStatus.ARCHIVED:
                    cp.status = CurrencyPairStatus.RESTORED
                    self._repository.update(uuid=cp.uuid, item=cp)

    def run(self) -> None:
        sleep_duration_s: int = 5

        refresh_period_s: int = 60
        refresh_counter_start: int = refresh_period_s // sleep_duration_s

        snapshot_period_s: int = environment.snapshot_period_s
        snapshot_counter_start = snapshot_period_s // sleep_duration_s

        refresh_counter: int = 0
        snapshot_counter: int = 0

        while not self._stopped:
            if refresh_counter <= 0:
                self._refresh()

                refresh_counter = refresh_counter_start

            if snapshot_counter <= 0:
                self._data_collector.create_snapshot()

                snapshot_counter = snapshot_counter_start

            refresh_counter -= 1
            snapshot_counter -= 1

            time.sleep(sleep_duration_s)

    def on_init(self) -> None:
        self.start()

    def on_destroy(self) -> None:
        self._stopped = True
        self.join()
