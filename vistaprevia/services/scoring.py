from dataclasses import dataclass, field

from vistaprevia.models import Producto
from vistaprevia.services.analytics import (
    HistoricalAnalytics,
    HistoricalAnalyticsService,
)


@dataclass(frozen=True)
class ScoreComponent:
    """
    Representa una dimensión individual del QuantEdge Score.
    """

    name: str
    score: float
    max_score: float
    explanation: str

    @property
    def percentage(self) -> float:
        if self.max_score == 0:
            return 0.0

        return round(
            (self.score / self.max_score) * 100,
            2,
        )


@dataclass(frozen=True)
class QuantEdgeScore:
    """
    Resultado final producido por el motor cuantitativo.
    """

    total_score: float
    recommendation: str
    confidence: float
    components: list[ScoreComponent] = field(
        default_factory=list
    )

    @property
    def rounded_score(self) -> int:
        return round(self.total_score)


class QuantEdgeScoringEngine:
    """
    Motor de scoring cuantitativo de QuantEdge.

    Score máximo:
        Trend       -> 30
        Momentum    -> 25
        Risk        -> 20
        Performance -> 20
        Liquidity   -> 5

    Total:
        100 puntos.
    """

    MAX_SCORE = 100.0

    def __init__(
        self,
        activo: Producto,
        *,
        interval: str = "1day",
        limit: int = 100,
    ):
        self.activo = activo
        self.interval = interval
        self.limit = limit

    def calculate(self) -> QuantEdgeScore:
        analytics = HistoricalAnalyticsService(
            self.activo,
            interval=self.interval,
            limit=self.limit,
        ).build()

        if analytics.observations < 20:
            return self._insufficient_data_result(
                analytics
            )

        components = [
            self._score_trend(analytics),
            self._score_momentum(analytics),
            self._score_risk(analytics),
            self._score_performance(analytics),
            self._score_liquidity(analytics),
        ]

        total_score = sum(
            component.score
            for component in components
        )

        total_score = round(
            min(
                max(total_score, 0.0),
                self.MAX_SCORE,
            ),
            2,
        )

        recommendation = (
            self._calculate_recommendation(
                total_score
            )
        )

        confidence = (
            self._calculate_confidence(
                analytics
            )
        )

        return QuantEdgeScore(
            total_score=total_score,
            recommendation=recommendation,
            confidence=confidence,
            components=components,
        )

    # ============================================================
    # TREND
    # ============================================================

    def _score_trend(
        self,
        analytics: HistoricalAnalytics,
    ) -> ScoreComponent:
        max_score = 30.0
        score = 15.0

        if analytics.trend == "Alcista":
            if analytics.trend_strength == "Fuerte":
                score = 30.0
            elif analytics.trend_strength == "Moderada":
                score = 26.0
            else:
                score = 22.0

        elif analytics.trend == "Bajista":
            if analytics.trend_strength == "Fuerte":
                score = 3.0
            elif analytics.trend_strength == "Moderada":
                score = 7.0
            else:
                score = 11.0

        elif analytics.trend == "Lateral / Mixta":
            score = 15.0

        explanation = (
            f"Tendencia {analytics.trend.lower()} "
            f"con fuerza "
            f"{analytics.trend_strength.lower()}."
        )

        return ScoreComponent(
            name="Tendencia",
            score=score,
            max_score=max_score,
            explanation=explanation,
        )

    # ============================================================
    # MOMENTUM
    # ============================================================

    def _score_momentum(
        self,
        analytics: HistoricalAnalytics,
    ) -> ScoreComponent:
        max_score = 25.0
        rsi = analytics.rsi_14

        if rsi is None:
            return ScoreComponent(
                name="Momentum",
                score=12.5,
                max_score=max_score,
                explanation=(
                    "No existen datos suficientes "
                    "para calcular RSI 14."
                ),
            )

        if 50 <= rsi <= 65:
            score = 25.0
            explanation = (
                "RSI positivo sin señales extremas "
                "de sobrecompra."
            )

        elif 40 <= rsi < 50:
            score = 19.0
            explanation = (
                "RSI neutral con momentum moderado."
            )

        elif 30 <= rsi < 40:
            score = 13.0
            explanation = (
                "RSI débil, cercano a zona "
                "de sobreventa."
            )

        elif rsi < 30:
            score = 10.0
            explanation = (
                "RSI en zona de sobreventa. "
                "Puede existir debilidad significativa "
                "o potencial reversión."
            )

        elif 65 < rsi <= 75:
            score = 20.0
            explanation = (
                "Momentum fuerte, aunque el RSI "
                "empieza a mostrar sobreextensión."
            )

        else:
            score = 14.0
            explanation = (
                "RSI elevado con riesgo creciente "
                "de sobrecompra."
            )

        return ScoreComponent(
            name="Momentum",
            score=score,
            max_score=max_score,
            explanation=explanation,
        )

    # ============================================================
    # RISK
    # ============================================================

    def _score_risk(
        self,
        analytics: HistoricalAnalytics,
    ) -> ScoreComponent:
        max_score = 20.0

        volatility = (
            analytics.annualized_volatility
        )

        drawdown = analytics.max_drawdown

        volatility_score = 10.0
        drawdown_score = 10.0

        if volatility is not None:
            if volatility < 15:
                volatility_score = 10.0
            elif volatility < 25:
                volatility_score = 8.0
            elif volatility < 40:
                volatility_score = 6.0
            elif volatility < 60:
                volatility_score = 3.0
            else:
                volatility_score = 1.0

        if drawdown is not None:
            absolute_drawdown = abs(drawdown)

            if absolute_drawdown < 5:
                drawdown_score = 10.0
            elif absolute_drawdown < 10:
                drawdown_score = 8.0
            elif absolute_drawdown < 20:
                drawdown_score = 6.0
            elif absolute_drawdown < 30:
                drawdown_score = 3.0
            else:
                drawdown_score = 1.0

        score = (
            volatility_score
            + drawdown_score
        )

        explanation = (
            "Evalúa conjuntamente volatilidad "
            "anualizada y maximum drawdown."
        )

        return ScoreComponent(
            name="Riesgo",
            score=score,
            max_score=max_score,
            explanation=explanation,
        )

    # ============================================================
    # PERFORMANCE
    # ============================================================

    def _score_performance(
        self,
        analytics: HistoricalAnalytics,
    ) -> ScoreComponent:
        max_score = 20.0
        performance = analytics.period_return

        if performance is None:
            score = 10.0
            explanation = (
                "No existen suficientes datos "
                "para evaluar rendimiento."
            )

        elif performance >= 20:
            score = 20.0
            explanation = (
                "Rendimiento muy positivo "
                "durante el período analizado."
            )

        elif performance >= 10:
            score = 17.0
            explanation = (
                "Rendimiento positivo significativo."
            )

        elif performance >= 3:
            score = 14.0
            explanation = (
                "Rendimiento positivo moderado."
            )

        elif performance >= 0:
            score = 11.0
            explanation = (
                "Rendimiento ligeramente positivo."
            )

        elif performance >= -5:
            score = 8.0
            explanation = (
                "Rendimiento ligeramente negativo."
            )

        elif performance >= -15:
            score = 5.0
            explanation = (
                "Rendimiento negativo relevante."
            )

        else:
            score = 2.0
            explanation = (
                "Rendimiento fuertemente negativo."
            )

        return ScoreComponent(
            name="Performance",
            score=score,
            max_score=max_score,
            explanation=explanation,
        )

    # ============================================================
    # LIQUIDITY
    # ============================================================

    def _score_liquidity(
        self,
        analytics: HistoricalAnalytics,
    ) -> ScoreComponent:
        max_score = 5.0

        volume = analytics.average_volume

        if volume is None:
            score = 2.5
            explanation = (
                "No existen suficientes datos "
                "de volumen."
            )

        elif volume >= 10_000_000:
            score = 5.0
            explanation = (
                "Nivel de liquidez muy elevado."
            )

        elif volume >= 1_000_000:
            score = 4.0
            explanation = (
                "Nivel de liquidez elevado."
            )

        elif volume >= 250_000:
            score = 3.0
            explanation = (
                "Liquidez intermedia."
            )

        elif volume >= 50_000:
            score = 2.0
            explanation = (
                "Liquidez relativamente baja."
            )

        else:
            score = 1.0
            explanation = (
                "Liquidez reducida."
            )

        return ScoreComponent(
            name="Liquidez",
            score=score,
            max_score=max_score,
            explanation=explanation,
        )

    # ============================================================
    # RECOMMENDATION
    # ============================================================

    @staticmethod
    def _calculate_recommendation(
        score: float,
    ) -> str:
        if score >= 80:
            return "Compra fuerte"

        if score >= 65:
            return "Compra"

        if score >= 50:
            return "Mantener"

        if score >= 35:
            return "Reducir"

        return "Venta"

    # ============================================================
    # CONFIDENCE
    # ============================================================

    @staticmethod
    def _calculate_confidence(
        analytics: HistoricalAnalytics,
    ) -> float:
        """
        Confianza inicial basada en disponibilidad
        y riqueza de datos.

        No representa probabilidad de rentabilidad.
        """

        observations = (
            analytics.observations
        )

        if observations >= 100:
            confidence = 95.0
        elif observations >= 75:
            confidence = 90.0
        elif observations >= 50:
            confidence = 85.0
        elif observations >= 30:
            confidence = 75.0
        elif observations >= 20:
            confidence = 65.0
        else:
            confidence = 40.0

        return confidence

    # ============================================================
    # INSUFFICIENT DATA
    # ============================================================

    @staticmethod
    def _insufficient_data_result(
        analytics: HistoricalAnalytics,
    ) -> QuantEdgeScore:
        return QuantEdgeScore(
            total_score=0.0,
            recommendation="Datos insuficientes",
            confidence=0.0,
            components=[],
        )