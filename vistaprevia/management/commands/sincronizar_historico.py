from django.core.management.base import BaseCommand

from vistaprevia.models import Producto
from vistaprevia.services.historical_sync import (
    HistoricalMarketDataService,
)


class Command(BaseCommand):
    help = (
        "Sincroniza el histórico de cotizaciones "
        "de los activos de QuantEdge."
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
            "--interval",
            type=str,
            default="1day",
            help=(
                "Intervalo solicitado a Twelve Data. "
                "Por defecto: 1day."
            ),
        )

        parser.add_argument(
            "--outputsize",
            type=int,
            default=100,
            help=(
                "Cantidad de cotizaciones históricas "
                "a solicitar. Por defecto: 100."
            ),
        )

    def handle(self, *args, **options):
        symbol = options.get("symbol")
        interval = options["interval"]
        outputsize = options["outputsize"]

        if outputsize < 1 or outputsize > 5000:
            self.stderr.write(
                self.style.ERROR(
                    "--outputsize debe estar entre 1 y 5000."
                )
            )
            return

        queryset = Producto.objects.filter(
            activo=True,
        )

        if symbol:
            normalized_symbol = (
                symbol.strip().upper()
            )

            queryset = queryset.filter(
                simbolo__iexact=normalized_symbol,
            )

        if not queryset.exists():
            self.stdout.write(
                self.style.WARNING(
                    "No se encontraron activos activos "
                    "para sincronizar."
                )
            )
            return

        try:
            service = HistoricalMarketDataService()

        except Exception as exc:
            self.stderr.write(
                self.style.ERROR(
                    "No fue posible iniciar el servicio "
                    f"de datos de mercado: {exc}"
                )
            )
            return

        exitosos = 0
        errores = 0
        total_recibidas = 0
        total_creadas = 0
        total_actualizadas = 0

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "QuantEdge | Sincronización histórica"
            )
        )

        self.stdout.write(
            (
                f"Intervalo: {interval} | "
                f"Registros solicitados: {outputsize}"
            )
        )

        self.stdout.write("")

        for activo in queryset.iterator():
            ticker = activo.ticker_mercado

            self.stdout.write(
                (
                    f"Sincronizando {activo.simbolo} "
                    f"({ticker})..."
                )
            )

            resultado = service.sincronizar_activo(
                activo,
                interval=interval,
                outputsize=outputsize,
            )

            if resultado.success:
                exitosos += 1

                total_recibidas += (
                    resultado.recibidas
                )

                total_creadas += (
                    resultado.creadas
                )

                total_actualizadas += (
                    resultado.actualizadas
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        (
                            f"  OK | "
                            f"recibidas={resultado.recibidas} | "
                            f"creadas={resultado.creadas} | "
                            f"actualizadas="
                            f"{resultado.actualizadas}"
                        )
                    )
                )

            else:
                errores += 1

                self.stderr.write(
                    self.style.ERROR(
                        (
                            f"  ERROR | "
                            f"{resultado.message}"
                        )
                    )
                )

        self.stdout.write("")

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "Resumen"
            )
        )

        self.stdout.write(
            f"Activos procesados: {exitosos + errores}"
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Sincronizados correctamente: {exitosos}"
            )
        )

        if errores:
            self.stdout.write(
                self.style.WARNING(
                    f"Con errores: {errores}"
                )
            )

        self.stdout.write(
            f"Cotizaciones recibidas: {total_recibidas}"
        )

        self.stdout.write(
            f"Nuevas cotizaciones: {total_creadas}"
        )

        self.stdout.write(
            (
                "Cotizaciones actualizadas: "
                f"{total_actualizadas}"
            )
        )