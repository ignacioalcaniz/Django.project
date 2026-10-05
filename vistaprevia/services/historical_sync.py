from decimal import Decimal
from dataclasses import dataclass

from django.db import transaction

from vistaprevia.exceptions import MarketDataError
from vistaprevia.models import (
    CotizacionHistorica,
    Producto,
)

from .market_data import TwelveDataClient


@dataclass(frozen=True)
class HistoricalSyncResult:
    activo_id: int
    simbolo: str
    ticker: str
    intervalo: str

    success: bool

    recibidas: int
    creadas: int
    actualizadas: int

    message: str


class HistoricalMarketDataService:
    PROVIDER_NAME = "twelve_data"

    def __init__(
        self,
        client=None,
    ):
        self.client = (
            client
            or TwelveDataClient()
        )

    def sincronizar_activo(
        self,
        activo: Producto,
        *,
        interval: str = "1day",
        outputsize: int = 100,
        force: bool = False,
    ) -> HistoricalSyncResult:
        ticker = activo.ticker_mercado

        if not activo.activo and not force:
            return HistoricalSyncResult(
                activo_id=activo.pk,
                simbolo=activo.simbolo,
                ticker=ticker,
                intervalo=interval,
                success=False,
                recibidas=0,
                creadas=0,
                actualizadas=0,
                message=(
                    "El activo se encuentra desactivado."
                ),
            )

        if not ticker:
            return HistoricalSyncResult(
                activo_id=activo.pk,
                simbolo=activo.simbolo,
                ticker=ticker,
                intervalo=interval,
                success=False,
                recibidas=0,
                creadas=0,
                actualizadas=0,
                message=(
                    "El activo no posee un ticker válido."
                ),
            )

        try:
            barras = self.client.get_time_series(
                ticker,
                interval=interval,
                outputsize=outputsize,
            )

        except MarketDataError as exc:
            return HistoricalSyncResult(
                activo_id=activo.pk,
                simbolo=activo.simbolo,
                ticker=ticker,
                intervalo=interval,
                success=False,
                recibidas=0,
                creadas=0,
                actualizadas=0,
                message=str(exc),
            )

        if any(not Decimal(str(value)).is_finite() for barra in barras
               for value in (barra.open_price, barra.high, barra.low, barra.close, barra.volume)):
            return HistoricalSyncResult(activo.pk, activo.simbolo, ticker, interval, False, len(barras), 0, 0,
                                        "Datos historicos no finitos.")

        creadas = 0
        actualizadas = 0

        with transaction.atomic():
            for barra in barras:
                _, creada = (
                    CotizacionHistorica.objects.update_or_create(
                        activo=activo,
                        fecha_hora=barra.datetime,
                        intervalo=interval,
                        proveedor=self.PROVIDER_NAME,
                        defaults={
                            "apertura": (
                                barra.open_price
                            ),
                            "maximo": barra.high,
                            "minimo": barra.low,
                            "cierre": barra.close,
                            "volumen": barra.volume,
                        },
                    )
                )

                if creada:
                    creadas += 1
                else:
                    actualizadas += 1

        return HistoricalSyncResult(
            activo_id=activo.pk,
            simbolo=activo.simbolo,
            ticker=ticker,
            intervalo=interval,
            success=True,
            recibidas=len(barras),
            creadas=creadas,
            actualizadas=actualizadas,
            message=(
                f"{activo.simbolo}: "
                f"{len(barras)} cotizaciones procesadas."
            ),
        )