from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from vistaprevia.models import Producto
from vistaprevia.services.analytics import HistoricalAnalyticsService
from vistaprevia.services.scoring import QuantEdgeScoringEngine

from .permissions import ProductoPermission
from .serializers import (
    CotizacionHistoricaSerializer,
    ProductoSerializer,
)


class ProductoViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    API REST de activos financieros de QuantEdge.

    Operaciones disponibles:
        GET     -> consulta
        POST    -> creación autorizada
        PUT     -> actualización autorizada
        PATCH   -> actualización parcial autorizada

    DELETE físico no forma parte de la API.
    Los activos se retiran mediante desactivación lógica
    utilizando activo=False.
    """

    serializer_class = ProductoSerializer
    permission_classes = [ProductoPermission]

    def get_queryset(self):
        queryset = Producto.objects.all().order_by("nombre")

        user = self.request.user

        if (
            user.is_authenticated
            and user.is_staff
            and user.has_perm("vistaprevia.change_producto")
        ):
            return queryset

        return queryset.filter(activo=True)

    @staticmethod
    def _obtener_intervalo_y_limite(request, minimo=1):
        intervalo = request.query_params.get(
            "intervalo",
            "1day",
        )

        try:
            limite = int(
                request.query_params.get(
                    "limite",
                    100,
                )
            )
        except (TypeError, ValueError):
            limite = 100

        limite = max(
            minimo,
            min(limite, 500),
        )

        return intervalo, limite

    @staticmethod
    def _intervalos_validos(activo):
        return {
            choice[0]
            for choice in activo.cotizaciones_historicas.model.INTERVALOS
        }

    @action(
        detail=True,
        methods=["get"],
        url_path="historico",
        permission_classes=[AllowAny],
    )
    def historico(self, request, pk=None):
        """
        Devuelve cotizaciones históricas almacenadas
        localmente para el activo seleccionado.
        """

        activo = self.get_object()

        intervalo, limite = self._obtener_intervalo_y_limite(
            request
        )

        intervalos_validos = self._intervalos_validos(
            activo
        )

        if intervalo not in intervalos_validos:
            return Response(
                {
                    "detail": "Intervalo no válido.",
                    "intervalos_validos": sorted(
                        intervalos_validos
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        cotizaciones = (
            activo.cotizaciones_historicas
            .filter(intervalo=intervalo)
            .order_by("-fecha_hora")[:limite]
        )

        serializer = CotizacionHistoricaSerializer(
            cotizaciones,
            many=True,
        )

        return Response(
            {
                "activo": {
                    "id": activo.id,
                    "simbolo": activo.simbolo,
                    "nombre": activo.nombre,
                },
                "intervalo": intervalo,
                "count": len(serializer.data),
                "results": serializer.data,
            }
        )

    @action(
        detail=True,
        methods=["get"],
        url_path="analytics",
        permission_classes=[AllowAny],
    )
    def analytics(self, request, pk=None):
        """
        Devuelve métricas cuantitativas calculadas
        desde el histórico almacenado localmente.
        """

        activo = self.get_object()

        intervalo, limite = self._obtener_intervalo_y_limite(
            request,
            minimo=20,
        )

        intervalos_validos = self._intervalos_validos(
            activo
        )

        if intervalo not in intervalos_validos:
            return Response(
                {
                    "detail": "Intervalo no válido.",
                    "intervalos_validos": sorted(
                        intervalos_validos
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        analytics_service = HistoricalAnalyticsService(
            activo,
            interval=intervalo,
            limit=limite,
        )

        analytics = analytics_service.build()

        return Response(
            {
                "activo": {
                    "id": activo.id,
                    "simbolo": activo.simbolo,
                    "nombre": activo.nombre,
                },
                "configuracion": {
                    "intervalo": intervalo,
                    "limite": limite,
                    "observaciones": analytics.observations,
                },
                "rendimiento": {
                    "retorno_periodo": analytics.period_return,
                    "volatilidad_anualizada": (
                        analytics.annualized_volatility
                    ),
                    "max_drawdown": analytics.max_drawdown,
                    "maximo_periodo": analytics.period_high,
                    "minimo_periodo": analytics.period_low,
                },
                "indicadores": {
                    "sma_20": analytics.sma_20,
                    "sma_50": analytics.sma_50,
                    "rsi_14": analytics.rsi_14,
                    "volumen_promedio": analytics.average_volume,
                },
                "tendencia": {
                    "clasificacion": analytics.trend,
                    "fortaleza": analytics.trend_strength,
                },
                "series": {
                    "labels": analytics.labels,
                    "precios": analytics.prices,
                    "volumenes": analytics.volumes,
                    "sma_20": analytics.sma_20_series,
                    "sma_50": analytics.sma_50_series,
                },
            }
        )

    @action(
        detail=True,
        methods=["get"],
        url_path="score",
        permission_classes=[AllowAny],
    )
    def score(self, request, pk=None):
        """
        Calcula el score QuantEdge actual sin modificar
        el score persistido del activo.
        """

        activo = self.get_object()

        intervalo, limite = self._obtener_intervalo_y_limite(
            request,
            minimo=20,
        )

        intervalos_validos = self._intervalos_validos(
            activo
        )

        if intervalo not in intervalos_validos:
            return Response(
                {
                    "detail": "Intervalo no válido.",
                    "intervalos_validos": sorted(
                        intervalos_validos
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        scoring_engine = QuantEdgeScoringEngine(
            activo,
            interval=intervalo,
            limit=limite,
        )

        resultado = scoring_engine.calculate()

        return Response(
            {
                "activo": {
                    "id": activo.id,
                    "simbolo": activo.simbolo,
                    "nombre": activo.nombre,
                },
                "configuracion": {
                    "intervalo": intervalo,
                    "limite": limite,
                },
               "score_actual": {
    "puntaje": resultado.rounded_score,
    "recomendacion": resultado.recommendation,
    "cobertura_datos": resultado.confidence,
    "componentes": [
        {
            "nombre": componente.name,
            "puntaje": componente.score,
            "puntaje_maximo": componente.max_score,
            "explicacion": componente.explanation,
        }
        for componente in resultado.components
    ],
},
                "score_persistido": {
                    "puntaje": activo.puntaje_quant,
                    "recomendacion": activo.get_recomendacion_display(),
                    "cobertura_datos": activo.cobertura_datos_quant,
                    "version": activo.version_score_quant,
                    "fecha_calculo": activo.fecha_ultimo_score_quant,
                },
                "sincronizado": (
                    activo.fecha_ultimo_score_quant is not None
                    and resultado.rounded_score
                    == activo.puntaje_quant
                ),
                "disclaimer": (
                    "El score QuantEdge es un indicador "
                    "cuantitativo determinístico. La cobertura "
                    "de datos representa disponibilidad de datos "
                    "y no probabilidad de rendimiento futuro."
                ),
            }
        )


class RankingView(APIView):
    """
    Ranking público de activos calculados por
    QuantEdge Scoring Engine.
    """

    permission_classes = [AllowAny]

    def get(self, request):
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

        serializer = ProductoSerializer(
            activos,
            many=True,
            context={
                "request": request,
            },
        )

        return Response(
            {
                "count": activos.count(),
                "results": serializer.data,
            }
        )