from django.urls import path
from .views import ActivoDetalleView, comparar_activos, ranking_activos

urlpatterns = [
    path("activo/<int:pk>/", ActivoDetalleView.as_view(), name="activo_detalle"),
    path("comparador/", comparar_activos, name="comparador_activos"),
    path("ranking/", ranking_activos, name="ranking_activos"),
]