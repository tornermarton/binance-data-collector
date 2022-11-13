# coding=utf-8
import datetime

from binance_data_collector.api import Controller, Get, Post

from .app_service import AppService
from .constants import TZ
from .dto.currency_pair_change_response_dto import CurrencyPairChangeResponseDTO
from .dto.currency_pair_response_dto import CurrencyPairResponseDTO
from .dto.health_reponse_dto import HealthResponseDTO
from .dto.info_response_dto import InfoResponseDTO
from .models.currency_pair import CurrencyPair
from .models.currency_pair_change import CurrencyPairChange


@Controller("/")
class AppController(object):
    def __init__(self, app_service: AppService) -> None:
        self._app_service: AppService = app_service

    @Get()
    def get_info(self) -> InfoResponseDTO:
        last_change: CurrencyPairChange = self._app_service.get_last_change()

        return InfoResponseDTO(
            time=datetime.datetime.now(tz=TZ),
            timezone=str(TZ),
            last_update_dt=self._app_service.get_last_update_dt(),
            last_change_dt=self._app_service.get_last_change_dt(),
            last_change=CurrencyPairChangeResponseDTO(
                added=[
                    CurrencyPairResponseDTO(
                        symbol=c.symbol,
                        base=c.base,
                        quote=c.quote,
                        is_active=self._app_service.is_active(currency_pair=c),
                    )
                    for c in last_change.added
                ],
                removed=[
                    CurrencyPairResponseDTO(
                        symbol=c.symbol,
                        base=c.base,
                        quote=c.quote,
                        is_active=False,
                    )
                    for c in last_change.removed
                ],
            ),
        )

    @Get("health")
    def get_health(self) -> HealthResponseDTO:
        return HealthResponseDTO(status="OK")

    @Get("currency_pairs")
    def get_currency_pairs(self) -> list[CurrencyPairResponseDTO]:
        return [
            CurrencyPairResponseDTO(
                symbol=c.symbol,
                base=c.base,
                quote=c.quote,
                is_active=self._app_service.is_active(currency_pair=c),
            )
            for c in self._app_service.get_currency_pairs()
        ]

    @Get("currency_pairs/{symbol}")
    def get_currency_pair(self, symbol: str) -> CurrencyPairResponseDTO:
        currency_pair: CurrencyPair = self._app_service.get_currency_pair(
            symbol=symbol,
        )

        return CurrencyPairResponseDTO(
            symbol=currency_pair.symbol,
            base=currency_pair.base,
            quote=currency_pair.quote,
            is_active=self._app_service.is_active(currency_pair=currency_pair),
        )

    @Post("currency_pairs/{symbol}/activate", status_code=204)
    def activate_currency_pair(self, symbol: str) -> None:
        self._app_service.activate_currency_pair(symbol=symbol)

    @Post("currency_pairs/{symbol}/deactivate", status_code=204)
    def deactivate_currency_pair(self, symbol: str) -> None:
        self._app_service.deactivate_currency_pair(symbol=symbol)
