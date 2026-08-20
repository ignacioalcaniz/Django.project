from django.core.management.base import BaseCommand

from vistaprevia.exceptions import MarketDataError
from vistaprevia.models import Producto
from vistaprevia.services.market_sync import (
    MarketDataSyncService,
)


class Command(BaseCommand):
    help = (
        "Sincroniza datos de mercado de los activos "
        "utilizando el servicio de market data de QuantEdge."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--symbol",
            type=str,
            help=(
                "Sincroniza solamente el activo "
                "correspondiente al símbolo indicado."
            ),
        )

        parser.add_argument(
            "--force",
            action="store_true",
            help=(
                "Fuerza la sincronización aunque el activo "
                "tenga desactivada la sincronización automática."
            ),
        )

    def handle(self, *args, **options):
        symbol = options.get("symbol")
        force = options.get("force", False)

        queryset = Producto.objects.filter(
            activo=True,
        )

        if not force:
            queryset = queryset.filter(
                sincronizacion_automatica=True,
            )

        if symbol:
            normalized_symbol = symbol.strip().upper()

            queryset = queryset.filter(
                simbolo__iexact=normalized_symbol,
            )

        if not queryset.exists():
            self.stdout.write(
                self.style.WARNING(
                    "No se encontraron activos "
                    "para sincronizar."
                )
            )
            return

        try:
            service = MarketDataSyncService()

        except MarketDataError as exc:
            self.stderr.write(
                self.style.ERROR(
                    f"No fue posible iniciar "
                    f"el servicio de mercado: {exc}"
                )
            )
            return

        actualizados = 0
        errores = 0

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "QuantEdge Market Data Sync"
            )
        )

        self.stdout.write(
            f"Activos encontrados: {queryset.count()}"
        )

        if force:
            self.stdout.write(
                self.style.WARNING(
                    "Modo forzado activado."
                )
            )

        self.stdout.write("")

        for activo in queryset.iterator():
            self.stdout.write(
                (
                    f"Sincronizando "
                    f"{activo.simbolo} "
                    f"({activo.ticker_mercado})..."
                )
            )

            resultado = service.sincronizar_activo(
                activo,
                force=force,
            )

            if resultado.success:
                actualizados += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"OK - {resultado.message}"
                    )
                )

            else:
                errores += 1

                self.stderr.write(
                    self.style.ERROR(
                        f"ERROR - {activo.simbolo}: "
                        f"{resultado.message}"
                    )
                )

        self.stdout.write("")

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "Resumen de sincronización"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Actualizados correctamente: "
                f"{actualizados}"
            )
        )

        if errores:
            self.stdout.write(
                self.style.WARNING(
                    f"Con errores: {errores}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "Con errores: 0"
                )
            )