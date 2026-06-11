from django.contrib import admin
from .models import ConsultaContacto


@admin.register(ConsultaContacto)
class ConsultaContactoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nombre",
        "email",
        "categoria",
        "estado",
        "fecha_creacion",
    )
    search_fields = (
        "nombre",
        "email",
        "asunto",
        "mensaje",
    )
    list_filter = (
        "categoria",
        "estado",
        "fecha_creacion",
    )
    ordering = ("-fecha_creacion",)
    list_editable = ("estado",)
    list_per_page = 20

    fieldsets = (
        ("Datos del contacto", {
            "fields": (
                "usuario",
                "nombre",
                "email",
            )
        }),
        ("Consulta", {
            "fields": (
                "categoria",
                "asunto",
                "mensaje",
            )
        }),
        ("Gestión interna", {
            "fields": (
                "estado",
                "fecha_creacion",
            )
        }),
    )

    readonly_fields = ("fecha_creacion",)
