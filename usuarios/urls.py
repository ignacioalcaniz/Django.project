from django.urls import path

from .views import (
    registro,
    dashboard,
    perfil_usuario,
    comprar_activo,
    asesorar_activo,
    alternar_favorito,
    cerrar_sesion,
    detalle_analisis,
    historial_ia,
    notificaciones,
    marcar_notificaciones_leidas,
)

urlpatterns = [
    path("registro/", registro, name="registro"),
    path("dashboard/", dashboard, name="dashboard"),
    path("perfil/", perfil_usuario, name="perfil_usuario"),

    path("comprar/<int:activo_id>/", comprar_activo, name="comprar_activo"),
    path("asesorar/<int:activo_id>/", asesorar_activo, name="asesorar_activo"),

    path("favorito/<int:activo_id>/", alternar_favorito, name="alternar_favorito"),

    path(
        "analisis/<int:consulta_id>/",
        detalle_analisis,
        name="detalle_analisis"
    ),

    path(
        "mis-analisis/",
        historial_ia,
        name="historial_ia"
    ),

    path(
        "notificaciones/",
        notificaciones,
        name="notificaciones"
    ),

    path(
        "notificaciones/marcar-leidas/",
        marcar_notificaciones_leidas,
        name="marcar_notificaciones_leidas"
    ),

    path("logout/", cerrar_sesion, name="cerrar_sesion"),
]