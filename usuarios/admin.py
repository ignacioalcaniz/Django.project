from django.contrib import admin
from .models import InversionSimulada, ConsultaIA


@admin.register(InversionSimulada)
class InversionSimuladaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "usuario",
        "activo",
        "cantidad",
        "precio_compra",
        "total_invertido_admin",
        "activa",
        "fecha_compra",
    )
    search_fields = (
        "usuario__username",
        "usuario__email",
        "activo__nombre",
        "activo__simbolo",
    )
    list_filter = (
        "activa",
        "fecha_compra",
        "activo",
    )
    ordering = ("-fecha_compra",)
    list_per_page = 20

    def total_invertido_admin(self, obj):
        return obj.total_invertido()

    total_invertido_admin.short_description = "Total invertido"


@admin.register(ConsultaIA)
class ConsultaIAAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "usuario",
        "activo",
        "fecha_creacion",
    )
    search_fields = (
        "usuario__username",
        "usuario__email",
        "activo__nombre",
        "activo__simbolo",
        "pregunta",
        "respuesta",
    )
    list_filter = (
        "fecha_creacion",
        "activo",
    )
    ordering = ("-fecha_creacion",)
    list_per_page = 20
