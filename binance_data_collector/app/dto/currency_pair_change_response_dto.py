# coding=utf-8
import pydantic

from .currency_pair_response_dto import CurrencyPairResponseDTO


class CurrencyPairChangeResponseDTO(pydantic.BaseModel):
    added: list[CurrencyPairResponseDTO]
    removed: list[CurrencyPairResponseDTO]
