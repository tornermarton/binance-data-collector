# coding=utf-8
from __future__ import annotations

import pydantic

from binance_data_collector.app.models.currency_pair import CurrencyPairStatus


class CurrencyPairsQueryDTO(pydantic.BaseModel):
    base: str | None = None
    quote: str | None = None
    status: CurrencyPairStatus | None = None
