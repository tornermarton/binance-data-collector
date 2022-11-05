# coding=utf-8
import datetime

import pydantic

from .currency_pair_change_response_dto import CurrencyPairChangeResponseDTO


class InfoResponseDTO(pydantic.BaseModel):
    time: datetime.datetime
    timezone: str
    last_update_dt: datetime.datetime
    last_change_dt: datetime.datetime
    last_change: CurrencyPairChangeResponseDTO
