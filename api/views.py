from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView
from rest_framework.exceptions import MethodNotAllowed, ValidationError
from rest_framework.throttling import ScopedRateThrottle
from vistaprevia.services.score_sync import QuantEdgeScoreSyncService

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
        queryset = Producto.objects.all().order_by(
            "nombre",
            "id",
        )

        user = self.request.user

        if (
            user.is_authenticated
            and user.is_staff
            and user.has_perm("vistaprevia.change_producto")
        ):
            return queryset

        return queryset.filter(activo=True)

    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def initial(self, request, *args, **kwargs):
        if request.method == "DELETE":
            raise MethodNotAllowed("DELETE")
        super().initial(request, *args, **kwargs)

    def get_throttles(self):
        if self.action in {"analytics", "score", "historico"}:
            self.throttle_scope = "quantitative"
            return [ScopedRateThrottle()]
        return super().get_throttles()

    @staticmethod
    def _obtener_intervalo_y_limite(request):
        intervalo = request.query_params.get(
            "intervalo",
            "1day",
        )

        raw = request.query_params.get("limite", "100")
        if not raw.isascii() or not raw.isdecimal() or len(raw) > 3:
            raise ValidationError({"limite": "Debe ser un entero entre 1 y 500."})
        limite = int(raw)
        if not 1 <= limite <= 500:
            raise ValidationError({"limite": "Debe estar entre 1 y 500."})

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

        El histórico puede consultarse utilizando cualquiera
        de los intervalos soportados por CotizacionHistorica.
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
            .order_by("-fecha_hora", "-id")[:limite]
        )

        serializer = CotizacionHistoricaSerializer(
            list(reversed(list(cotizaciones))),
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
        a partir del histórico diario almacenado localmente.

        QuantEdge Analytics v1 utiliza exclusivamente
        observaciones con intervalo 1day.
        """

        activo = self.get_object()

        intervalo, limite = self._obtener_intervalo_y_limite(
            request,
        )

        if intervalo != "1day":
            return Response(
                {
                    "detail": (
                        "QuantEdge Analytics actualmente "
                        "soporta únicamente el intervalo 1day."
                    ),
                    "intervalo_soportado": "1day",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        analytics_service = HistoricalAnalyticsService(
            activo,
            interval="1day",
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
                    "intervalo": "1day",
                    "limite": limite,
                    "observaciones": analytics.observations,
                },
                "rendimiento": {
                    "retorno_periodo": (
                        analytics.period_return
                    ),
                    "volatilidad_anualizada": (
                        analytics.annualized_volatility
                    ),
                    "max_drawdown": (
                        analytics.max_drawdown
                    ),
                    "maximo_periodo": (
                        analytics.period_high
                    ),
                    "minimo_periodo": (
                        analytics.period_low
                    ),
                },
                "indicadores": {
                    "sma_20": analytics.sma_20,
                    "sma_50": analytics.sma_50,
                    "rsi_14": analytics.rsi_14,
                    "volumen_promedio": (
                        analytics.average_volume
                    ),
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
        Calcula el score QuantEdge actual utilizando
        histórico diario.

        El cálculo no modifica el score persistido
        del activo.

        QuantEdge Scoring Engine v1 utiliza exclusivamente
        observaciones con intervalo 1day.
        """

        activo = self.get_object()

        intervalo, limite = self._obtener_intervalo_y_limite(
            request,
        )

        if intervalo != "1day":
            return Response(
                {
                    "detail": (
                        "QuantEdge Scoring Engine actualmente "
                        "soporta únicamente el intervalo 1day."
                    ),
                    "intervalo_soportado": "1day",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        scoring_engine = QuantEdgeScoringEngine(
            activo,
            interval="1day",
            limit=limite,
        )

        resultado = scoring_engine.calculate()

        componentes = [
            {
                "nombre": componente.name,
                "puntaje": componente.score,
                "puntaje_maximo": componente.max_score,
                "explicacion": componente.explanation,
            }
            for componente in resultado.components
        ]

        return Response(
            {
                "activo": {
                    "id": activo.id,
                    "simbolo": activo.simbolo,
                    "nombre": activo.nombre,
                },
                "configuracion": {
                    "intervalo": "1day",
                    "limite": limite,
                },
                "score_actual": {
                    "puntaje": resultado.rounded_score,
                    "recomendacion": (
                        resultado.recommendation
                    ),
                    "cobertura_datos": (
                        resultado.confidence
                    ),
                    "componentes": componentes,
                },
                "score_persistido": {
                    "puntaje": activo.puntaje_quant,
                    "recomendacion": (
                        activo.get_recomendacion_display()
                    ),
                    "cobertura_datos": (
                        activo.cobertura_datos_quant
                    ),
                    "version": (
                        activo.version_score_quant
                    ),
                    "fecha_calculo": (
                        activo.fecha_ultimo_score_quant
                    ),
                },
                "sincronizado": (
                    activo.fecha_ultimo_score_quant is not None
                    and resultado.recommendation != "Datos insuficientes"
                    and resultado.rounded_score == activo.puntaje_quant
                    and QuantEdgeScoreSyncService.RECOMMENDATION_MAP.get(resultado.recommendation) == activo.recomendacion
                    and round(resultado.confidence) == activo.cobertura_datos_quant
                    and activo.version_score_quant == QuantEdgeScoreSyncService.SCORE_VERSION
                    and not activo.cotizaciones_historicas.filter(
                        intervalo="1day", fecha_creacion__gt=activo.fecha_ultimo_score_quant
                    ).exists()
                    and (activo.fecha_ultima_sincronizacion is None
                         or activo.fecha_ultimo_score_quant >= activo.fecha_ultima_sincronizacion)
                ),
                "disclaimer": (
                    "El score QuantEdge es un indicador "
                    "cuantitativo determinístico. La cobertura "
                    "de datos representa disponibilidad de datos "
                    "y no probabilidad de rendimiento futuro."
                ),
            }
        )


class RankingView(GenericAPIView):
    """
    Ranking público de activos calculados por
    QuantEdge Scoring Engine.

    Utiliza exclusivamente scores previamente
    persistidos en la base de datos.
    """

    serializer_class = ProductoSerializer
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
                "id",
            )
        )

        page = self.paginate_queryset(activos)
        serializer = ProductoSerializer(
            page,
            many=True,
            context={
                "request": request,
            },
        )

        return self.get_paginated_response(serializer.data)
