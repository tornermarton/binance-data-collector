# coding=utf-8
from __future__ import annotations

import typing

from binance_data_collector.api import HTTPException, Inject, Injectable

from .constants import REPOSITORY_TOKEN
from .helpers.data_collector import DataCollector
from .models.currency_pair import CurrencyPair, CurrencyPairStatus
from .models.repository import EntityNotFoundException, Repository


@Injectable()
class AppService(object):
    def __init__(
        self,
        data_collector: DataCollector,
        repository: Repository[CurrencyPair] = Inject(token=REPOSITORY_TOKEN)
    ) -> None:
        self._data_collector: DataCollector = data_collector
        self._repository: Repository[CurrencyPair] = repository

    def get_currency_pairs(
        self,
        query: dict[str, typing.Any] | None = None,
    ) -> list[CurrencyPair]:
        return self._repository.find(query=query)

    def get_currency_pair(self, uuid: str) -> CurrencyPair:
        try:
            return self._repository.read(uuid=uuid)
        except EntityNotFoundException as e:
            raise HTTPException(
                status_code=404,
                detail=f"CurrencyPair [{uuid}] cannot be found",
            ) from e

    def start_currency_pair(self, uuid: str) -> None:
        currency_pair: CurrencyPair = self.get_currency_pair(uuid=uuid)

        if currency_pair.status == CurrencyPairStatus.ARCHIVED:
            raise HTTPException(
                status_code=403,
                detail=f"CurrencyPair [{uuid}] is archived",
            )

        if (
            currency_pair.status == CurrencyPairStatus.ACTIVE
            or
            currency_pair.status == CurrencyPairStatus.IDLE
        ):
            raise HTTPException(
                status_code=403,
                detail=f"CurrencyPair [{uuid}] is already started",
            )

        currency_pair.status = CurrencyPairStatus.ACTIVE
        self._repository.update(uuid=currency_pair.uuid, item=currency_pair)
        self._data_collector.add_currency_pair(currency_pair=currency_pair)

    def stop_currency_pair(self, uuid: str) -> None:
        currency_pair: CurrencyPair = self.get_currency_pair(uuid=uuid)

        if currency_pair.status == CurrencyPairStatus.ARCHIVED:
            raise HTTPException(
                status_code=403,
                detail=f"CurrencyPair [{uuid}] is archived",
            )

        if (
            currency_pair.status != CurrencyPairStatus.ACTIVE
            and
            currency_pair.status != CurrencyPairStatus.IDLE
        ):
            raise HTTPException(
                status_code=403,
                detail=f"CurrencyPair [{uuid}] is not started",
            )

        currency_pair.status = CurrencyPairStatus.STOPPED
        self._repository.update(uuid=currency_pair.uuid, item=currency_pair)
        self._data_collector.remove_currency_pair(currency_pair=currency_pair)
