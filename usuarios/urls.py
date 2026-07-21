from django.urls import path

from .views import (
    alternar_favorito,
    asesorar_activo,
    buscar_activos_ajax,
    cerrar_sesion,
    comprar_activo,
    dashboard,
    detalle_analisis,
    historial_ia,
    marcar_notificaciones_leidas,
    notificaciones,
    perfil_usuario,
    registro,
)


urlpatterns = [
    # Autenticación y cuenta
    path("registro/", registro, name="registro"),
    path("dashboard/", dashboard, name="dashboard"),
    path("perfil/", perfil_usuario, name="perfil_usuario"),
    path("logout/", cerrar_sesion, name="cerrar_sesion"),

    # Mercado y operaciones
    path(
        "ajax/activos/",
        buscar_activos_ajax,
        name="buscar_activos_ajax",
    ),
    path(
        "comprar/<int:activo_id>/",
        comprar_activo,
        name="comprar_activo",
    ),
    path(
        "asesorar/<int:activo_id>/",
        asesorar_activo,
        name="asesorar_activo",
    ),
    path(
        "favorito/<int:activo_id>/",
        alternar_favorito,
        name="alternar_favorito",
    ),

    # Inteligencia artificial
    path(
        "analisis/<int:consulta_id>/",
        detalle_analisis,
        name="detalle_analisis",
    ),
    path(
        "mis-analisis/",
        historial_ia,
        name="historial_ia",
    ),

    # Notificaciones
    path(
        "notificaciones/",
        notificaciones,
        name="notificaciones",
    ),
    path(
        "notificaciones/marcar-leidas/",
        marcar_notificaciones_leidas,
        name="marcar_notificaciones_leidas",
    ),
]