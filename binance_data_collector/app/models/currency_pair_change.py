# coding=utf-8
import dataclasses

from .currency_pair import CurrencyPair


@dataclasses.dataclass(frozen=True)
class CurrencyPairChange(object):
    added: set[CurrencyPair] = dataclasses.field(default_factory=set)
    removed: set[CurrencyPair] = dataclasses.field(default_factory=set)
