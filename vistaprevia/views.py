from html import unescape

from django.shortcuts import render
from django.utils.html import strip_tags
from django.utils.text import Truncator
from django.views.generic import DetailView

from usuarios.models import ActivoFavorito

from .models import Producto
from .services.analytics import (
    HistoricalAnalyticsService,
)
from .services.scoring import (
    QuantEdgeScoringEngine,
)


class ActivoDetalleView(DetailView):
    model = Producto

    template_name = (
        "vistaprevia/activo_detalle.html"
    )

    context_object_name = "activo"

    def get_queryset(self):
        return Producto.objects.filter(
            activo=True
        )

    def get_context_data(
        self,
        **kwargs,
    ):
        context = super().get_context_data(
            **kwargs
        )

        activo = self.object

        description = " ".join(strip_tags(unescape(activo.descripcion)).split())
        if not description:
            description = (
                f"Consultá el análisis de {activo.nombre} ({activo.simbolo}), "
                f"{activo.get_tipo_activo_display()}: indicadores y datos financieros en QuantEdge."
            )
        context.update({
            "seo_title": f"{activo.nombre} ({activo.simbolo}) | QuantEdge",
            "seo_description": Truncator(description).chars(160),
            "canonical_url": self.request.build_absolute_uri(activo.get_absolute_url()),
            "seo_type": "website",
            "seo_image_url": (
                self.request.build_absolute_uri(activo.imagen.url)
                if activo.imagen else None
            ),
        })

        # ========================================================
        # MÉTRICAS FUNDAMENTALES
        # ========================================================

        context["metricas"] = [
            (
                "Capitalización",
                activo.capitalizacion_mercado,
            ),
            (
                "Volumen",
                activo.volumen,
            ),
            (
                "Volumen promedio",
                activo.volumen_promedio,
            ),
            (
                "P/E Ratio",
                activo.pe_ratio,
            ),
            (
                "EPS",
                activo.eps,
            ),
            (
                "Beta",
                activo.beta,
            ),
            (
                "Dividendo",
                activo.dividendo,
            ),
        ]

        # ========================================================
        # ANALYTICS HISTÓRICO
        # ========================================================

        analytics_service = (
            HistoricalAnalyticsService(
                activo,
                interval="1day",
                limit=100,
            )
        )

        analytics = (
            analytics_service.build()
        )

        context[
            "historical_analytics"
        ] = analytics

        context[
            "historical_labels"
        ] = analytics.labels

        context[
            "historical_prices"
        ] = analytics.prices

        context[
            "historical_volumes"
        ] = analytics.volumes

        context[
            "historical_sma_20"
        ] = analytics.sma_20_series

        context[
            "historical_sma_50"
        ] = analytics.sma_50_series

        # ========================================================
        # QUANTEDGE SCORING ENGINE
        # ========================================================

        scoring_engine = (
            QuantEdgeScoringEngine(
                activo,
                interval="1day",
                limit=100,
            )
        )

        quant_score = (
            scoring_engine.calculate()
        )

        context[
            "quant_score"
        ] = quant_score

        context[
            "quant_score_components"
        ] = quant_score.components

        context[
            "quant_score_value"
        ] = quant_score.rounded_score

        context[
            "quant_recommendation"
        ] = quant_score.recommendation

        context[
            "quant_confidence"
        ] = quant_score.confidence

        # ========================================================
        # WATCHLIST
        # ========================================================

        if self.request.user.is_authenticated:
            context["es_favorito"] = (
                ActivoFavorito.objects.filter(
                    usuario=self.request.user,
                    activo=activo,
                ).exists()
            )

        else:
            context[
                "es_favorito"
            ] = False

        return context


def comparar_activos(request):
    activos = (
        Producto.objects
        .filter(
            activo=True
        )
        .order_by(
            "nombre"
        )
    )

    activo_1 = None
    activo_2 = None

    activo_1_id = request.GET.get(
        "activo_1"
    )

    activo_2_id = request.GET.get(
        "activo_2"
    )

    if activo_1_id:
        activo_1 = (
            Producto.objects
            .filter(
                id=activo_1_id,
                activo=True,
            )
            .first()
        )

    if activo_2_id:
        activo_2 = (
            Producto.objects
            .filter(
                id=activo_2_id,
                activo=True,
            )
            .first()
        )

    contexto = {
        "activos": activos,
        "activo_1": activo_1,
        "activo_2": activo_2,
    }

    return render(
        request,
        "vistaprevia/comparador.html",
        contexto,
    )

def ranking_activos(request):
    activos = (
        Producto.objects
        .filter(
            activo=True,
            fecha_ultimo_score_quant__isnull=False,
        )
        .order_by(
            "-puntaje_quant",
            "-cobertura_datos_quant",
            "nombre",
        )
    )

    return render(
        request,
        "vistaprevia/ranking.html",
        {
            "activos": activos,
        },
    )
