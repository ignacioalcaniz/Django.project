from dataclasses import dataclass
from math import sqrt
from statistics import pstdev

from vistaprevia.models import (
    CotizacionHistorica,
    Producto,
)


@dataclass(frozen=True)
class HistoricalAnalytics:
    # Datos para visualización
    labels: list[str]
    prices: list[float]
    volumes: list[int]

    sma_20_series: list[float | None]
    sma_50_series: list[float | None]

    # Información general
    observations: int

    # Rendimiento y riesgo
    period_return: float | None
    annualized_volatility: float | None
    max_drawdown: float | None

    # Rangos
    period_high: float | None
    period_low: float | None

    # Indicadores
    sma_20: float | None
    sma_50: float | None
    rsi_14: float | None
    average_volume: float | None

    # Interpretación
    trend: str
    trend_strength: str


class HistoricalAnalyticsService:
    """
    Motor de analytics de series temporales de QuantEdge.

    Trabaja exclusivamente con datos almacenados en
    CotizacionHistorica.

    No consulta APIs externas.
    """

    TRADING_DAYS_PER_YEAR = 252

    def __init__(
        self,
        activo: Producto,
        *,
        interval: str = "1day",
        limit: int = 100,
    ):
        self.activo = activo
        self.interval = interval

        self.limit = max(
            2,
            min(int(limit), 5000),
        )

    def build(self) -> HistoricalAnalytics:
        cotizaciones = list(
            CotizacionHistorica.objects
            .filter(
                activo=self.activo,
                intervalo=self.interval,
            )
            .order_by("-fecha_hora")[:self.limit]
        )

        # Para cálculos financieros necesitamos
        # orden temporal ascendente.
        cotizaciones.reverse()

        if not cotizaciones:
            return self._empty_result()

        cierres = [
            float(cotizacion.cierre)
            for cotizacion in cotizaciones
        ]

        volumenes = [
            int(cotizacion.volumen)
            for cotizacion in cotizaciones
        ]

        labels = [
            cotizacion.fecha_hora.strftime(
                "%d/%m/%Y"
            )
            for cotizacion in cotizaciones
        ]

        retornos = self._calculate_returns(
            cierres
        )

        sma_20_series = (
            self._moving_average_series(
                cierres,
                period=20,
            )
        )

        sma_50_series = (
            self._moving_average_series(
                cierres,
                period=50,
            )
        )

        sma_20 = self._simple_moving_average(
            cierres,
            period=20,
        )

        sma_50 = self._simple_moving_average(
            cierres,
            period=50,
        )

        rsi_14 = self._calculate_rsi(
            cierres,
            period=14,
        )

        trend, trend_strength = (
            self._calculate_trend(
                prices=cierres,
                sma_20=sma_20,
                sma_50=sma_50,
            )
        )

        return HistoricalAnalytics(
            labels=labels,
            prices=cierres,
            volumes=volumenes,

            sma_20_series=sma_20_series,
            sma_50_series=sma_50_series,

            observations=len(cotizaciones),

            period_return=self._period_return(
                cierres
            ),

            annualized_volatility=(
                self._annualized_volatility(
                    retornos
                )
            ),

            max_drawdown=(
                self._max_drawdown(
                    cierres
                )
            ),

            period_high=max(cierres),
            period_low=min(cierres),

            sma_20=sma_20,
            sma_50=sma_50,
            rsi_14=rsi_14,

            average_volume=(
                sum(volumenes) / len(volumenes)
                if volumenes
                else None
            ),

            trend=trend,
            trend_strength=trend_strength,
        )

    # ============================================================
    # RETORNOS
    # ============================================================

    @staticmethod
    def _calculate_returns(
        prices: list[float],
    ) -> list[float]:
        returns = []

        for previous, current in zip(
            prices,
            prices[1:],
        ):
            if previous == 0:
                continue

            returns.append(
                (current / previous) - 1
            )

        return returns

    @staticmethod
    def _period_return(
        prices: list[float],
    ) -> float | None:
        if len(prices) < 2:
            return None

        initial_price = prices[0]
        final_price = prices[-1]

        if initial_price == 0:
            return None

        return (
            (final_price / initial_price) - 1
        ) * 100

    # ============================================================
    # VOLATILIDAD
    # ============================================================

    def _annualized_volatility(
        self,
        returns: list[float],
    ) -> float | None:
        if len(returns) < 2:
            return None

        daily_volatility = pstdev(
            returns
        )

        return (
            daily_volatility
            * sqrt(
                self.TRADING_DAYS_PER_YEAR
            )
            * 100
        )

    # ============================================================
    # MOVING AVERAGES
    # ============================================================

    @staticmethod
    def _simple_moving_average(
        prices: list[float],
        *,
        period: int,
    ) -> float | None:
        if len(prices) < period:
            return None

        values = prices[-period:]

        return sum(values) / period

    @staticmethod
    def _moving_average_series(
        prices: list[float],
        *,
        period: int,
    ) -> list[float | None]:
        series = []

        for index in range(
            len(prices)
        ):
            if index + 1 < period:
                series.append(None)
                continue

            window = prices[
                index + 1 - period:
                index + 1
            ]

            average = (
                sum(window) / period
            )

            series.append(
                round(
                    average,
                    6,
                )
            )

        return series

    # ============================================================
    # RSI
    # ============================================================

    @staticmethod
    def _calculate_rsi(
        prices: list[float],
        *,
        period: int = 14,
    ) -> float | None:
        if len(prices) <= period:
            return None

        cambios = [
            current - previous
            for previous, current in zip(
                prices,
                prices[1:],
            )
        ]

        recientes = cambios[-period:]

        ganancias = [
            max(cambio, 0)
            for cambio in recientes
        ]

        perdidas = [
            abs(min(cambio, 0))
            for cambio in recientes
        ]

        promedio_ganancias = (
            sum(ganancias) / period
        )

        promedio_perdidas = (
            sum(perdidas) / period
        )

        if promedio_perdidas == 0:
            return 100.0

        relative_strength = (
            promedio_ganancias
            / promedio_perdidas
        )

        rsi = (
            100
            - (
                100
                / (
                    1
                    + relative_strength
                )
            )
        )

        return rsi

    # ============================================================
    # MAX DRAWDOWN
    # ============================================================

    @staticmethod
    def _max_drawdown(
        prices: list[float],
    ) -> float | None:
        if len(prices) < 2:
            return None

        peak = prices[0]
        max_drawdown = 0.0

        for price in prices:
            if price > peak:
                peak = price

            if peak == 0:
                continue

            drawdown = (
                (price - peak)
                / peak
            )

            if drawdown < max_drawdown:
                max_drawdown = drawdown

        return (
            max_drawdown
            * 100
        )

    # ============================================================
    # TREND ENGINE
    # ============================================================

    @staticmethod
    def _calculate_trend(
        *,
        prices: list[float],
        sma_20: float | None,
        sma_50: float | None,
    ) -> tuple[str, str]:
        if (
            not prices
            or sma_20 is None
            or sma_50 is None
        ):
            return (
                "Sin datos suficientes",
                "Indeterminada",
            )

        current_price = prices[-1]

        if (
            current_price > sma_20
            and sma_20 > sma_50
        ):
            distance = (
                (current_price - sma_50)
                / sma_50
            ) * 100

            if distance >= 10:
                strength = "Fuerte"
            elif distance >= 4:
                strength = "Moderada"
            else:
                strength = "Débil"

            return (
                "Alcista",
                strength,
            )

        if (
            current_price < sma_20
            and sma_20 < sma_50
        ):
            distance = (
                (sma_50 - current_price)
                / sma_50
            ) * 100

            if distance >= 10:
                strength = "Fuerte"
            elif distance >= 4:
                strength = "Moderada"
            else:
                strength = "Débil"

            return (
                "Bajista",
                strength,
            )

        return (
            "Lateral / Mixta",
            "Neutral",
        )

    # ============================================================
    # EMPTY RESULT
    # ============================================================

    @staticmethod
    def _empty_result():
        return HistoricalAnalytics(
            labels=[],
            prices=[],
            volumes=[],

            sma_20_series=[],
            sma_50_series=[],

            observations=0,

            period_return=None,
            annualized_volatility=None,
            max_drawdown=None,

            period_high=None,
            period_low=None,

            sma_20=None,
            sma_50=None,
            rsi_14=None,
            average_volume=None,

            trend="Sin datos",
            trend_strength="Indeterminada",
        )