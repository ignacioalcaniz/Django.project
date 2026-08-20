from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from vistaprevia.exceptions import MarketDataError
from vistaprevia.models import Producto

from .market_data import TwelveDataClient


@dataclass(frozen=True)
class MarketSyncResult:
    activo_id: int
    simbolo: str
    ticker: str
    success: bool
    message: str


class MarketDataSyncService:
    """
    Servicio de aplicación responsable de sincronizar
    datos externos de mercado con el dominio QuantEdge.

    La capa HTTP queda encapsulada en TwelveDataClient.
    """

    PROVIDER_NAME = "twelve_data"

    def __init__(self, client=None):
        self.client = client or TwelveDataClient()

    def sincronizar_activo(
        self,
        activo: Producto,
        *,
        force: bool = False,
    ) -> MarketSyncResult:
        ahora = timezone.now()
        ticker = activo.ticker_mercado

        if not activo.activo:
            return MarketSyncResult(
                activo_id=activo.pk,
                simbolo=activo.simbolo,
                ticker=ticker,
                success=False,
                message="El activo se encuentra desactivado.",
            )

        if (
            not force
            and not activo.sincronizacion_automatica
        ):
            return MarketSyncResult(
                activo_id=activo.pk,
                simbolo=activo.simbolo,
                ticker=ticker,
                success=False,
                message=(
                    "La sincronización automática "
                    "está desactivada."
                ),
            )

        if not ticker:
            return self._registrar_error(
                activo,
                "El activo no posee un ticker válido.",
                ahora,
            )

        Producto.objects.filter(
            pk=activo.pk
        ).update(
            fecha_ultimo_intento_sincronizacion=ahora,
        )

        try:
            quote = self.client.get_quote(ticker)

        except MarketDataError as exc:
            return self._registrar_error(
                activo,
                str(exc),
                ahora,
            )

        monedas_validas = dict(
            Producto.MONEDAS
        )

        with transaction.atomic():
            activo.precio_actual = quote.price
            activo.apertura = quote.open_price
            activo.cierre_anterior = quote.previous_close
            activo.maximo_dia = quote.high
            activo.minimo_dia = quote.low
            activo.variacion_diaria = quote.percent_change
            activo.volumen = quote.volume

            if quote.exchange:
                activo.bolsa = quote.exchange

            if quote.currency in monedas_validas:
                activo.moneda = quote.currency

            activo.proveedor_datos = self.PROVIDER_NAME
            activo.estado_sincronizacion = "sincronizado"

            activo.fecha_ultimo_intento_sincronizacion = (
                ahora
            )

            activo.fecha_ultima_sincronizacion = ahora

            activo.ultimo_error_sincronizacion = ""

            activo.save(
                update_fields=[
                    "precio_actual",
                    "apertura",
                    "cierre_anterior",
                    "maximo_dia",
                    "minimo_dia",
                    "variacion_diaria",
                    "volumen",
                    "bolsa",
                    "moneda",
                    "proveedor_datos",
                    "estado_sincronizacion",
                    "fecha_ultimo_intento_sincronizacion",
                    "fecha_ultima_sincronizacion",
                    "ultimo_error_sincronizacion",
                    "fecha_actualizacion",
                ]
            )

        return MarketSyncResult(
            activo_id=activo.pk,
            simbolo=activo.simbolo,
            ticker=ticker,
            success=True,
            message=(
                f"{activo.simbolo} sincronizado "
                f"correctamente a {quote.currency} "
                f"{quote.price}."
            ),
        )

    def sincronizar_queryset(
        self,
        queryset,
        *,
        force: bool = False,
    ):
        resultados = []

        for activo in queryset:
            resultado = self.sincronizar_activo(
                activo,
                force=force,
            )

            resultados.append(resultado)

        return resultados

    def _registrar_error(
        self,
        activo,
        mensaje,
        fecha_intento,
    ):
        mensaje_limpio = str(mensaje).strip()[:2000]

        Producto.objects.filter(
            pk=activo.pk
        ).update(
            proveedor_datos=self.PROVIDER_NAME,
            estado_sincronizacion="error",
            fecha_ultimo_intento_sincronizacion=(
                fecha_intento
            ),
            ultimo_error_sincronizacion=mensaje_limpio,
        )

        return MarketSyncResult(
            activo_id=activo.pk,
            simbolo=activo.simbolo,
            ticker=activo.ticker_mercado,
            success=False,
            message=mensaje_limpio,
        )