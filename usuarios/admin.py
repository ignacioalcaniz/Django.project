import csv

from django.contrib import admin
from django.http import HttpResponse
from django.utils.html import format_html

from .models import (
    PerfilUsuario,
    InversionSimulada,
    ConsultaIA,
    ActivoFavorito,
    Notificacion,
)


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "usuario",
        "nombre_completo",
        "perfil_badge",
        "capital_demo",
        "pais",
        "fecha_actualizacion",
    )
    search_fields = (
        "usuario__username",
        "usuario__email",
        "nombre_completo",
        "pais",
    )
    list_filter = (
        "perfil_inversor",
        "pais",
        "fecha_actualizacion",
    )
    ordering = ("usuario__username",)
    list_per_page = 20

    def perfil_badge(self, obj):
        colores = {
            "conservador": "#16a34a",
            "moderado": "#2563eb",
            "agresivo": "#dc2626",
        }
        return format_html(
            '<span style="background:{};" class="qe-badge-white">{}</span>',
            colores.get(obj.perfil_inversor, "#334155"),
            obj.get_perfil_inversor_display()
        )

    perfil_badge.short_description = "Perfil inversor"


@admin.register(InversionSimulada)
class InversionSimuladaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "usuario",
        "activo",
        "cantidad",
        "precio_compra",
        "total_invertido_admin",
        "valor_actual_admin",
        "resultado_admin",
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
    readonly_fields = ("fecha_compra",)
    actions = ("exportar_inversiones_csv",)

    @admin.action(description="Exportar inversiones seleccionadas a CSV")
    def exportar_inversiones_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="quantedge_inversiones.csv"'

        writer = csv.writer(response)
        writer.writerow([
            "ID",
            "Usuario",
            "Activo",
            "Cantidad",
            "Precio compra",
            "Total invertido",
            "Valor actual",
            "Resultado",
            "Rentabilidad %",
            "Activa",
            "Fecha",
        ])

        for inversion in queryset:
            writer.writerow([
                inversion.id,
                inversion.usuario.username,
                inversion.activo.simbolo,
                inversion.cantidad,
                inversion.precio_compra,
                inversion.total_invertido(),
                inversion.valor_actual(),
                inversion.ganancia_perdida(),
                inversion.rentabilidad_porcentual(),
                inversion.activa,
                inversion.fecha_compra,
            ])

        return response

    def total_invertido_admin(self, obj):
        return obj.total_invertido()

    total_invertido_admin.short_description = "Total invertido"

    def valor_actual_admin(self, obj):
        return obj.valor_actual()

    valor_actual_admin.short_description = "Valor actual"

    def resultado_admin(self, obj):
        resultado = obj.ganancia_perdida()

        if resultado >= 0:
            return format_html('<span class="qe-positive">+USD {}</span>', resultado)

        return format_html('<span class="qe-negative">USD {}</span>', resultado)

    resultado_admin.short_description = "Resultado"


@admin.register(ConsultaIA)
class ConsultaIAAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "usuario",
        "activo",
        "pregunta_corta",
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
    readonly_fields = ("fecha_creacion",)

    def pregunta_corta(self, obj):
        if obj.pregunta:
            return obj.pregunta[:70]
        return "Consulta general"

    pregunta_corta.short_description = "Pregunta"


@admin.register(ActivoFavorito)
class ActivoFavoritoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "usuario",
        "activo",
        "fecha_agregado",
    )
    search_fields = (
        "usuario__username",
        "usuario__email",
        "activo__nombre",
        "activo__simbolo",
    )
    list_filter = (
        "fecha_agregado",
        "activo",
    )
    ordering = ("-fecha_agregado",)
    list_per_page = 20


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "usuario",
        "tipo_badge",
        "titulo",
        "leida_badge",
        "fecha_creacion",
    )
    search_fields = (
        "usuario__username",
        "usuario__email",
        "titulo",
        "mensaje",
    )
    list_filter = (
        "tipo",
        "leida",
        "fecha_creacion",
    )
    ordering = ("-fecha_creacion",)
    list_per_page = 30
    actions = (
        "marcar_como_leidas",
        "marcar_como_no_leidas",
        "exportar_notificaciones_csv",
    )

    @admin.action(description="Marcar notificaciones como leídas")
    def marcar_como_leidas(self, request, queryset):
        updated = queryset.update(leida=True)
        self.message_user(request, f"{updated} notificación/es marcada/s como leídas.")

    @admin.action(description="Marcar notificaciones como no leídas")
    def marcar_como_no_leidas(self, request, queryset):
        updated = queryset.update(leida=False)
        self.message_user(request, f"{updated} notificación/es marcada/s como no leídas.")

    @admin.action(description="Exportar notificaciones seleccionadas a CSV")
    def exportar_notificaciones_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="quantedge_notificaciones.csv"'

        writer = csv.writer(response)
        writer.writerow([
            "ID",
            "Usuario",
            "Tipo",
            "Título",
            "Mensaje",
            "Leída",
            "Fecha",
        ])

        for n in queryset:
            writer.writerow([
                n.id,
                n.usuario.username,
                n.get_tipo_display(),
                n.titulo,
                n.mensaje,
                n.leida,
                n.fecha_creacion,
            ])

        return response

    def tipo_badge(self, obj):
        colores = {
            "sistema": "#64748b",
            "compra": "#16a34a",
            "favorito": "#f59e0b",
            "ia": "#7c3aed",
            "perfil": "#2563eb",
        }

        return format_html(
            '<span style="background:{};" class="qe-badge-white">{}</span>',
            colores.get(obj.tipo, "#334155"),
            obj.get_tipo_display()
        )

    tipo_badge.short_description = "Tipo"

    def leida_badge(self, obj):
        if obj.leida:
            return format_html('<span class="qe-neutral">Leída</span>')
        return format_html('<span class="qe-positive">Nueva</span>')

    leida_badge.short_description = "Estado"
