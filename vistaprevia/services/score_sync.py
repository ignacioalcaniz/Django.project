from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from vistaprevia.models import Producto
from vistaprevia.services.scoring import (
    QuantEdgeScore,
    QuantEdgeScoringEngine,
)


@dataclass(frozen=True)
class ScoreSyncResult:
    activo_id: int
    simbolo: str
    success: bool
    score: int | None
    recommendation: str
    data_coverage: int | None
    version: str
    message: str


class QuantEdgeScoreSyncService:
    """
    Calcula y persiste el resultado del QuantEdge Scoring Engine.

    Este servicio funciona como única capa responsable de trasladar
    los resultados del motor cuantitativo al modelo Producto.

    De esta manera, views, comandos, admin y futuras tareas Celery
    pueden reutilizar exactamente la misma lógica de persistencia.
    """

    SCORE_VERSION = "v1"

    RECOMMENDATION_MAP = {
        "Compra fuerte": "comprar",
        "Compra": "comprar",
        "Mantener": "mantener",
        "Reducir": "observar",
        "Venta": "vender",
    }

    def __init__(
        self,
        *,
        interval: str = "1day",
        limit: int = 100,
    ):
        self.interval = interval
        self.limit = limit

    def sincronizar_activo(
        self,
        activo: Producto,
    ) -> ScoreSyncResult:
        """
        Calcula el score de un activo y, si existen datos
        suficientes, persiste el resultado.
        """

        resultado = QuantEdgeScoringEngine(
            activo,
            interval=self.interval,
            limit=self.limit,
        ).calculate()

        if resultado.recommendation == "Datos insuficientes":
            return self._resultado_datos_insuficientes(
                activo,
                resultado,
            )

        recomendacion_modelo = (
            self._mapear_recomendacion(
                resultado.recommendation
            )
        )

        score = self._normalizar_porcentaje(
            resultado.rounded_score
        )

        cobertura = self._normalizar_porcentaje(
            resultado.confidence
        )

        with transaction.atomic():
            Producto.objects.filter(
                pk=activo.pk
            ).update(
                puntaje_quant=score,
                recomendacion=recomendacion_modelo,
                cobertura_datos_quant=cobertura,
                fecha_ultimo_score_quant=timezone.now(),
                version_score_quant=self.SCORE_VERSION,
            )

        # Mantenemos sincronizada la instancia recibida.
        activo.puntaje_quant = score
        activo.recomendacion = recomendacion_modelo
        activo.cobertura_datos_quant = cobertura
        activo.fecha_ultimo_score_quant = timezone.now()
        activo.version_score_quant = self.SCORE_VERSION

        return ScoreSyncResult(
            activo_id=activo.pk,
            simbolo=activo.simbolo,
            success=True,
            score=score,
            recommendation=recomendacion_modelo,
            data_coverage=cobertura,
            version=self.SCORE_VERSION,
            message=(
                f"{activo.simbolo}: score QuantEdge "
                f"actualizado a {score}/100."
            ),
        )

    def sincronizar_activos(
        self,
        activos,
    ) -> list[ScoreSyncResult]:
        """
        Sincroniza una colección de activos.

        Cada activo se procesa independientemente para que un fallo
        individual no impida obtener el resultado de los restantes.
        """

        resultados = []

        for activo in activos:
            try:
                resultado = self.sincronizar_activo(
                    activo
                )

            except Exception as exc:
                resultado = ScoreSyncResult(
                    activo_id=activo.pk,
                    simbolo=activo.simbolo,
                    success=False,
                    score=None,
                    recommendation="",
                    data_coverage=None,
                    version=self.SCORE_VERSION,
                    message=(
                        f"{activo.simbolo}: no fue posible "
                        f"actualizar el score. {exc}"
                    ),
                )

            resultados.append(
                resultado
            )

        return resultados

    def _mapear_recomendacion(
        self,
        recommendation: str,
    ) -> str:
        """
        Convierte la recomendación humana del Scoring Engine
        al valor interno admitido por Producto.recomendacion.
        """

        try:
            return self.RECOMMENDATION_MAP[
                recommendation
            ]

        except KeyError as exc:
            raise ValueError(
                "Recomendación del Scoring Engine "
                f"no reconocida: {recommendation!r}."
            ) from exc

    @staticmethod
    def _normalizar_porcentaje(
        value: float | int,
    ) -> int:
        """
        Garantiza un entero comprendido entre 0 y 100.
        """

        return max(
            0,
            min(
                100,
                round(value),
            ),
        )

    def _resultado_datos_insuficientes(
        self,
        activo: Producto,
        resultado: QuantEdgeScore,
    ) -> ScoreSyncResult:
        """
        No pisa un score previamente válido cuando el motor
        no dispone de suficientes observaciones.
        """

        return ScoreSyncResult(
            activo_id=activo.pk,
            simbolo=activo.simbolo,
            success=False,
            score=None,
            recommendation="",
            data_coverage=self._normalizar_porcentaje(
                resultado.confidence
            ),
            version=self.SCORE_VERSION,
            message=(
                f"{activo.simbolo}: datos históricos "
                "insuficientes para actualizar el score."
            ),
        )