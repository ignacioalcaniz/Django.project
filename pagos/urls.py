from django.urls import path
from . import views

app_name = "pagos"
urlpatterns = [
    path("checkout/<int:activo_id>/", views.checkout, name="checkout"),
    path("ordenes/<uuid:pk>/", views.orden_detalle, name="orden_detalle"),
    path("ordenes/<uuid:pk>/iniciar/", views.iniciar, name="iniciar"),
    path("ordenes/<uuid:pk>/estado/", views.estado, name="estado"),
    path("ordenes/<uuid:pk>/success/", views.resultado, {"outcome": "success"}, name="success"),
    path("ordenes/<uuid:pk>/pending/", views.resultado, {"outcome": "pending"}, name="pending"),
    path("ordenes/<uuid:pk>/failure/", views.resultado, {"outcome": "failure"}, name="failure"),
    path("historial/", views.historial, name="historial"),
    path("webhooks/mercadopago/", views.mercadopago_webhook, name="webhook"),
]
