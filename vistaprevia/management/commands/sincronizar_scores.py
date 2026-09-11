from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from vistaprevia.models import Producto
from vistaprevia.services.score_sync import (
    QuantEdgeScoreSyncService,
)


class Command(BaseCommand):
    help = (
        "Calcula y persiste el QuantEdge Score de los activos "
        "utilizando sus cotizaciones históricas almacenadas."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--simbolo",
            type=str,
            help=(
                "Sincroniza únicamente el activo correspondiente "
                "al símbolo indicado. Ejemplo: AAPL."
            ),
        )

        parser.add_argument(
            "--interval",
            type=str,
            default="1day",
            help=(
                "Intervalo histórico utilizado para calcular "
                "el score. Por defecto: 1day."
            ),
        )

        parser.add_argument(
            "--limit",
            type=int,
            default=100,
            help=(
                "Cantidad máxima de observaciones históricas "
                "utilizadas. Por defecto: 100."
            ),
        )

        parser.add_argument(
            "--incluir-inactivos",
            action="store_true",
            help=(
                "Incluye activos marcados como inactivos. "
                "Por defecto solo se procesan activos activos."
            ),
        )

    def handle(self, *args, **options):
        simbolo = options["simbolo"]
        interval = options["interval"]
        limit = options["limit"]
        incluir_inactivos = options[
            "incluir_inactivos"
        ]

        if limit < 20:
            raise CommandError(
                "--limit debe ser igual o superior a 20 "
                "para permitir el cálculo del QuantEdge Score."
            )

        queryset = Producto.objects.all()

        if not incluir_inactivos:
            queryset = queryset.filter(
                activo=True
            )

        if simbolo:
            simbolo = simbolo.strip().upper()

            queryset = queryset.filter(
                simbolo__iexact=simbolo
            )

            if not queryset.exists():
                raise CommandError(
                    f"No existe un activo disponible "
                    f"con símbolo '{simbolo}'."
                )

        queryset = queryset.order_by(
            "simbolo"
        )

        total = queryset.count()

        if total == 0:
            self.stdout.write(
                self.style.WARNING(
                    "No hay activos para procesar."
                )
            )
            return

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "QuantEdge Scoring Engine"
            )
        )

        self.stdout.write(
            f"Activos a procesar: {total}"
        )

        self.stdout.write(
            f"Intervalo: {interval}"
        )

        self.stdout.write(
            f"Observaciones máximas: {limit}"
        )

        self.stdout.write("")

        service = QuantEdgeScoreSyncService(
            interval=interval,
            limit=limit,
        )

        resultados = service.sincronizar_activos(
            queryset
        )

        exitosos = 0
        fallidos = 0

        for resultado in resultados:

            if resultado.success:
                exitosos += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        (
                            f"[OK] {resultado.simbolo} | "
                            f"Score: {resultado.score}/100 | "
                            f"Recomendación: "
                            f"{resultado.recommendation} | "
                            f"Cobertura: "
                            f"{resultado.data_coverage}% | "
                            f"Versión: {resultado.version}"
                        )
                    )
                )

            else:
                fallidos += 1

                self.stdout.write(
                    self.style.WARNING(
                        (
                            f"[SKIP/ERROR] "
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
            f"Procesados: {total}"
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Actualizados correctamente: {exitosos}"
            )
        )

        if fallidos:
            self.stdout.write(
                self.style.WARNING(
                    f"No actualizados: {fallidos}"
                )
            )

        self.stdout.write("")