# coding=utf-8
import datetime

import pydantic

from binance_data_collector.app.models.currency_pair import CurrencyPairStatus


class CurrencyPairResponseDTO(pydantic.BaseModel):
    uuid: str
    base: str
    quote: str
    status: CurrencyPairStatus
    created_at: datetime.datetime
    updated_at: datetime.datetime
