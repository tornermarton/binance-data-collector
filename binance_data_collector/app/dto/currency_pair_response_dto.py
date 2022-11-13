# coding=utf-8
import pydantic


class CurrencyPairResponseDTO(pydantic.BaseModel):
    symbol: str
    base: str
    quote: str
    is_active: bool
