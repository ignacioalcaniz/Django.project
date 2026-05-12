from django.urls import path
from .views import registro, dashboard, comprar_activo, asesorar_activo, cerrar_sesion

urlpatterns = [
    path("registro/", registro, name="registro"),
    path("dashboard/", dashboard, name="dashboard"),
    path("comprar/<int:activo_id>/", comprar_activo, name="comprar_activo"),
    path("asesorar/<int:activo_id>/", asesorar_activo, name="asesorar_activo"),
    path("logout/", cerrar_sesion, name="cerrar_sesion"),
]