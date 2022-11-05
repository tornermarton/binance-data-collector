# coding=utf-8
from __future__ import annotations

__all__ = ["CurrencyPair"]

import dataclasses


@dataclasses.dataclass(frozen=True)
class CurrencyPair(object):
    """Class for a currency pair (ticker pair).

    Currency pairs compare the value the base currency (first)
    the quote currency (second).
    """

    base: str
    quote: str

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> CurrencyPair:
        return cls(**data)

    def upper(self, separator: str = '_') -> str:
        return f"{self.base.upper()}{separator}{self.quote.upper()}"

    def lower(self, separator: str = '_') -> str:
        return f"{self.base.lower()}{separator}{self.quote.lower()}"

    @property
    def symbol(self) -> str:
        return self.lower('')
