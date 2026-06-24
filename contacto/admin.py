from django.contrib import admin
from django.utils.html import format_html

from .models import ConsultaContacto


@admin.register(ConsultaContacto)
class ConsultaContactoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nombre",
        "email",
        "categoria",
        "estado_badge",
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
    list_editable = ()
    list_per_page = 20
    readonly_fields = ("fecha_creacion",)
    actions = (
        "marcar_pendiente",
        "marcar_en_proceso",
        "marcar_resuelto",
    )

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

    @admin.action(description="Marcar como pendiente")
    def marcar_pendiente(self, request, queryset):
        updated = queryset.update(estado="pendiente")
        self.message_user(request, f"{updated} consulta/s marcada/s como pendiente.")

    @admin.action(description="Marcar como en proceso")
    def marcar_en_proceso(self, request, queryset):
        updated = queryset.update(estado="en_proceso")
        self.message_user(request, f"{updated} consulta/s marcada/s como en proceso.")

    @admin.action(description="Marcar como resuelto")
    def marcar_resuelto(self, request, queryset):
        updated = queryset.update(estado="resuelto")
        self.message_user(request, f"{updated} consulta/s marcada/s como resuelto.")

    def estado_badge(self, obj):
        colores = {
            "pendiente": "#f59e0b",
            "en_proceso": "#2563eb",
            "resuelto": "#16a34a",
            "cerrado": "#64748b",
        }

        return format_html(
            '<span style="background:{};" class="qe-badge-white">{}</span>',
            colores.get(obj.estado, "#334155"),
            obj.estado
        )

    estado_badge.short_description = "Estado"
