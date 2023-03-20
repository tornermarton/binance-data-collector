# coding=utf-8
__all__ = ["CurrencyPair", "CurrencyPairStatus"]

import dataclasses
import enum

from binance_data_collector.serialization import serializable

from binance_data_collector.app.models.repository import Model


class CurrencyPairStatus(enum.Enum):
    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    IDLE = "IDLE"
    STOPPED = "STOPPED"
    RESTORED = "RESTORED"
    ARCHIVED = "ARCHIVED"


@serializable()
@dataclasses.dataclass(kw_only=True)
class CurrencyPair(Model):
    """Class for a currency pair (ticker pair).

    Currency pairs compare the value of the base currency (first) to the quote
    currency (second).
    """

    base: str
    quote: str
    status: CurrencyPairStatus = CurrencyPairStatus.CREATED

    def upper(self, separator: str = '_') -> str:
        return f"{self.base.upper()}{separator}{self.quote.upper()}"

    def lower(self, separator: str = '_') -> str:
        return f"{self.base.lower()}{separator}{self.quote.lower()}"

    @property
    def symbol(self) -> str:
        return self.lower('')
