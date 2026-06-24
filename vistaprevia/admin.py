from django.contrib import admin
from django.utils.html import format_html

from .models import Producto


admin.site.site_header = "QuantEdge Admin | Inteligencia Bursátil"
admin.site.site_title = "QuantEdge"
admin.site.index_title = "Panel de administración de QuantEdge"


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "preview_imagen",
        "simbolo_badge",
        "nombre",
        "tipo_activo_badge",
        "precio_actual",
        "moneda",
        "variacion_coloreada",
        "riesgo_coloreado",
        "recomendacion_coloreada",
        "puntaje_quant_badge",
        "activo_coloreado",
        "destacado_coloreado",
    )

    list_display_links = ("id", "simbolo_badge", "nombre")
    list_editable = ("precio_actual",)

    search_fields = (
        "nombre",
        "simbolo",
        "ticker_externo",
        "sector",
        "industria",
        "pais",
        "bolsa",
        "descripcion",
        "nota_analista",
        "tesis_inversion",
    )

    list_filter = (
        "tipo_activo",
        "riesgo",
        "recomendacion",
        "moneda",
        "activo",
        "es_destacado",
        "sector",
        "industria",
        "pais",
        "bolsa",
        "fecha_creacion",
        "fecha_actualizacion",
        "fecha_ultima_revision",
    )

    ordering = ("-puntaje_quant", "nombre")
    list_per_page = 15
    save_on_top = True
    empty_value_display = "Sin dato"

    readonly_fields = (
        "preview_imagen",
        "fecha_creacion",
        "fecha_actualizacion",
    )

    actions = (
        "marcar_como_destacados",
        "quitar_destacados",
        "activar_activos",
        "desactivar_activos",
        "recomendar_comprar",
        "recomendar_mantener",
        "recomendar_observar",
        "recomendar_vender",
        "riesgo_bajo",
        "riesgo_medio",
        "riesgo_alto",
    )

    fieldsets = (
        ("Identidad del activo", {
            "fields": (
                "nombre",
                "simbolo",
                "ticker_externo",
                "descripcion",
            )
        }),
        ("Imagen corporativa", {
            "fields": (
                "imagen",
                "preview_imagen",
            )
        }),
        ("Clasificación de mercado", {
            "fields": (
                "tipo_activo",
                "sector",
                "industria",
                "pais",
                "bolsa",
                "moneda",
            )
        }),
        ("Precios y variaciones", {
            "fields": (
                "precio_actual",
                "precio_objetivo",
                "apertura",
                "cierre_anterior",
                "variacion_diaria",
                "variacion_semanal",
                "variacion_mensual",
                "maximo_dia",
                "minimo_dia",
                "maximo_52_semanas",
                "minimo_52_semanas",
            )
        }),
        ("Volumen y valoración", {
            "fields": (
                "volumen",
                "volumen_promedio",
                "capitalizacion_mercado",
                "pe_ratio",
                "eps",
                "dividendo",
                "beta",
            )
        }),
        ("Análisis QuantEdge", {
            "fields": (
                "riesgo",
                "recomendacion",
                "puntaje_quant",
                "confianza_modelo",
                "nota_analista",
                "tesis_inversion",
                "fecha_ultima_revision",
            )
        }),
        ("Estado operativo", {
            "fields": (
                "activo",
                "es_destacado",
            )
        }),
        ("Auditoría", {
            "fields": (
                "fecha_creacion",
                "fecha_actualizacion",
            )
        }),
    )

    @admin.action(description="Marcar seleccionados como destacados")
    def marcar_como_destacados(self, request, queryset):
        updated = queryset.update(es_destacado=True)
        self.message_user(request, f"{updated} activo/s marcado/s como destacados.")

    @admin.action(description="Quitar destacados")
    def quitar_destacados(self, request, queryset):
        updated = queryset.update(es_destacado=False)
        self.message_user(request, f"{updated} activo/s dejaron de estar destacados.")

    @admin.action(description="Activar activos")
    def activar_activos(self, request, queryset):
        updated = queryset.update(activo=True)
        self.message_user(request, f"{updated} activo/s activado/s.")

    @admin.action(description="Desactivar activos")
    def desactivar_activos(self, request, queryset):
        updated = queryset.update(activo=False)
        self.message_user(request, f"{updated} activo/s desactivado/s.")

    @admin.action(description="Cambiar recomendación a Comprar")
    def recomendar_comprar(self, request, queryset):
        updated = queryset.update(recomendacion="comprar")
        self.message_user(request, f"{updated} activo/s actualizado/s a Comprar.")

    @admin.action(description="Cambiar recomendación a Mantener")
    def recomendar_mantener(self, request, queryset):
        updated = queryset.update(recomendacion="mantener")
        self.message_user(request, f"{updated} activo/s actualizado/s a Mantener.")

    @admin.action(description="Cambiar recomendación a Observar")
    def recomendar_observar(self, request, queryset):
        updated = queryset.update(recomendacion="observar")
        self.message_user(request, f"{updated} activo/s actualizado/s a Observar.")

    @admin.action(description="Cambiar recomendación a Vender")
    def recomendar_vender(self, request, queryset):
        updated = queryset.update(recomendacion="vender")
        self.message_user(request, f"{updated} activo/s actualizado/s a Vender.")

    @admin.action(description="Cambiar riesgo a Bajo")
    def riesgo_bajo(self, request, queryset):
        updated = queryset.update(riesgo="bajo")
        self.message_user(request, f"{updated} activo/s actualizado/s a riesgo Bajo.")

    @admin.action(description="Cambiar riesgo a Medio")
    def riesgo_medio(self, request, queryset):
        updated = queryset.update(riesgo="medio")
        self.message_user(request, f"{updated} activo/s actualizado/s a riesgo Medio.")

    @admin.action(description="Cambiar riesgo a Alto")
    def riesgo_alto(self, request, queryset):
        updated = queryset.update(riesgo="alto")
        self.message_user(request, f"{updated} activo/s actualizado/s a riesgo Alto.")

    def preview_imagen(self, obj):
        if obj and obj.imagen:
            return format_html(
                '<img src="{}" width="58" height="58" style="border-radius:12px; object-fit:cover; border:2px solid #1e293b; box-shadow:0 4px 10px rgba(0,0,0,.18);" />',
                obj.imagen.url
            )
        return format_html('<span class="qe-admin-muted">Sin imagen</span>')

    preview_imagen.short_description = "Imagen"

    def simbolo_badge(self, obj):
        return format_html('<span class="qe-badge-dark">{}</span>', obj.simbolo)

    simbolo_badge.short_description = "Símbolo"

    def tipo_activo_badge(self, obj):
        colores = {
            "accion": "#2563eb",
            "etf": "#7c3aed",
            "crypto": "#f59e0b",
            "indice": "#0ea5e9",
            "bono": "#16a34a",
            "fondo": "#ec4899",
        }
        return format_html(
            '<span style="background:{};" class="qe-badge-white">{}</span>',
            colores.get(obj.tipo_activo, "#334155"),
            obj.get_tipo_activo_display()
        )

    tipo_activo_badge.short_description = "Tipo"

    def variacion_coloreada(self, obj):
        valor = float(obj.variacion_diaria or 0)

        if valor > 0:
            return format_html('<span class="qe-positive">+{:.2f}%</span>', valor)

        if valor < 0:
            return format_html('<span class="qe-negative">{:.2f}%</span>', valor)

        return format_html('<span class="qe-neutral">{:.2f}%</span>', valor)

    variacion_coloreada.short_description = "Variación"

    def riesgo_coloreado(self, obj):
        clases = {
            "bajo": "qe-positive",
            "medio": "qe-warning",
            "alto": "qe-negative",
        }
        return format_html(
            '<span class="{}">{}</span>',
            clases.get(obj.riesgo, "qe-neutral"),
            obj.get_riesgo_display()
        )

    riesgo_coloreado.short_description = "Riesgo"

    def recomendacion_coloreada(self, obj):
        clases = {
            "comprar": "qe-positive",
            "mantener": "qe-blue",
            "vender": "qe-negative",
            "observar": "qe-purple",
        }
        return format_html(
            '<span class="{}">{}</span>',
            clases.get(obj.recomendacion, "qe-neutral"),
            obj.get_recomendacion_display()
        )

    recomendacion_coloreada.short_description = "Recomendación"

    def puntaje_quant_badge(self, obj):
        if obj.puntaje_quant >= 80:
            clase = "qe-score-high"
        elif obj.puntaje_quant >= 60:
            clase = "qe-score-good"
        elif obj.puntaje_quant >= 40:
            clase = "qe-score-mid"
        else:
            clase = "qe-score-low"

        return format_html(
            '<span class="{}">{} / 100</span>',
            clase,
            obj.puntaje_quant
        )

    puntaje_quant_badge.short_description = "Score"

    def activo_coloreado(self, obj):
        if obj.activo:
            return format_html('<span class="qe-positive">Activo</span>')
        return format_html('<span class="qe-negative">Inactivo</span>')

    activo_coloreado.short_description = "Estado"

    def destacado_coloreado(self, obj):
        if obj.es_destacado:
            return format_html('<span class="qe-warning">★ Destacado</span>')
        return format_html('<span class="qe-neutral">Normal</span>')

    destacado_coloreado.short_description = "Visibilidad"

   

