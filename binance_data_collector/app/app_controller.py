# coding=utf-8
import datetime

from binance_data_collector.api import (
    Controller,
    Get,
    HttpStatus,
    Param,
    Post,
    Query,
    ParseUUIDPipe,
    UUIDVersion,
)

from .app_service import AppService
from .constants import TZ
from .dto.currency_pair_response_dto import CurrencyPairResponseDTO
from .dto.currency_pairs_query_dto import CurrencyPairsQueryDTO
from .dto.health_reponse_dto import HealthResponseDTO
from .dto.info_response_dto import InfoResponseDTO
from .models.currency_pair import CurrencyPair


@Controller("/")
class AppController(object):
    def __init__(self, app_service: AppService) -> None:
        self._app_service: AppService = app_service

    @Get()
    def get_info(self) -> InfoResponseDTO:
        return InfoResponseDTO(
            time=datetime.datetime.now(tz=TZ),
            timezone=str(TZ),
        )

    @Get("health")
    def get_health(self) -> HealthResponseDTO:
        return HealthResponseDTO(status="OK")

    @Get("currency_pairs", tags=["currency_pairs"])
    def get_currency_pairs(
        self,
        query: CurrencyPairsQueryDTO = Query(),
    ) -> list[CurrencyPairResponseDTO]:
        currency_pairs: list[CurrencyPair] = \
            self._app_service.get_currency_pairs(query=query.dict())

        return [
            CurrencyPairResponseDTO(
                uuid=currency_pair.uuid,
                base=currency_pair.base,
                quote=currency_pair.quote,
                status=currency_pair.status,
                created_at=currency_pair.created_at,
                updated_at=currency_pair.updated_at,
            )
            for currency_pair in currency_pairs
        ]

    @Get("currency_pairs/{uuid}", tags=["currency_pairs"])
    def get_currency_pair(
        self,
        uuid: str = Param("uuid", ParseUUIDPipe(version=UUIDVersion.V4)),
    ) -> CurrencyPairResponseDTO:
        currency_pair: CurrencyPair = self._app_service.get_currency_pair(
            uuid=uuid,
        )

        return CurrencyPairResponseDTO(
            uuid=currency_pair.symbol,
            base=currency_pair.base,
            quote=currency_pair.quote,
            status=currency_pair.status,
            created_at=currency_pair.created_at,
            updated_at=currency_pair.updated_at,
        )

    @Post(
        "currency_pairs/{uuid}/start",
        status_code=HttpStatus.NO_CONTENT,
        tags=["currency_pairs"],
    )
    def start_currency_pair(
        self,
        uuid: str = Param(name="uuid"),
    ) -> None:
        self._app_service.start_currency_pair(uuid=uuid)

    @Post(
        "currency_pairs/{uuid}/stop",
        status_code=HttpStatus.NO_CONTENT,
        tags=["currency_pairs"],
    )
    def stop_currency_pair(
        self,
        uuid: str = Param(name="uuid"),
    ) -> None:
        self._app_service.stop_currency_pair(uuid=uuid)
