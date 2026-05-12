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

    list_display_links = (
        "id",
        "simbolo_badge",
        "nombre",
    )

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

    ordering = ("nombre",)
    list_per_page = 12
    # date_hierarchy = "fecha_creacion"
    save_on_top = True
    empty_value_display = "Sin dato"

    list_editable = ("precio_actual",)

    readonly_fields = (
        "preview_imagen",
        "fecha_creacion",
        "fecha_actualizacion",
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

    def preview_imagen(self, obj):
        if obj and obj.imagen:
            return format_html(
                '<img src="{}" width="58" height="58" style="border-radius:12px; object-fit:cover; border:2px solid #1e293b; box-shadow: 0 4px 10px rgba(0,0,0,0.15);" />',
                obj.imagen.url
            )
        return "Sin imagen"

    preview_imagen.short_description = "Imagen"

    def simbolo_badge(self, obj):
        return format_html(
            '<span style="background:{}; color:{}; padding:6px 10px; border-radius:999px; font-weight:700;">{}</span>',
            "#0f172a",
            "#f8fafc",
            obj.simbolo
        )

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
            '<span style="background:{}; color:white; padding:6px 10px; border-radius:999px; font-weight:700;">{}</span>',
            colores.get(obj.tipo_activo, "#334155"),
            obj.get_tipo_activo_display()
        )

    tipo_activo_badge.short_description = "Tipo"

    def variacion_coloreada(self, obj):
        valor = float(obj.variacion_diaria or 0)
        if valor > 0:
            return format_html(
                '<span style="color:{}; font-weight:800;">+{}%</span>',
                "#16a34a",
                f"{valor:.2f}"
            )
        elif valor < 0:
            return format_html(
                '<span style="color:{}; font-weight:800;">{}%</span>',
                "#dc2626",
                f"{valor:.2f}"
            )
        return format_html(
            '<span style="color:{}; font-weight:800;">{}%</span>',
            "#64748b",
            f"{valor:.2f}"
        )

    variacion_coloreada.short_description = "Variación"

    def riesgo_coloreado(self, obj):
        colores = {
            "bajo": "#16a34a",
            "medio": "#f59e0b",
            "alto": "#dc2626",
        }
        return format_html(
            '<span style="color:{}; font-weight:800;">{}</span>',
            colores.get(obj.riesgo, "#64748b"),
            obj.get_riesgo_display()
        )

    riesgo_coloreado.short_description = "Riesgo"

    def recomendacion_coloreada(self, obj):
        colores = {
            "comprar": "#16a34a",
            "mantener": "#2563eb",
            "vender": "#dc2626",
            "observar": "#7c3aed",
        }
        return format_html(
            '<span style="color:{}; font-weight:800;">{}</span>',
            colores.get(obj.recomendacion, "#64748b"),
            obj.get_recomendacion_display()
        )

    recomendacion_coloreada.short_description = "Recomendación"

    def puntaje_quant_badge(self, obj):
        if obj.puntaje_quant >= 80:
            color = "#16a34a"
        elif obj.puntaje_quant >= 60:
            color = "#2563eb"
        elif obj.puntaje_quant >= 40:
            color = "#f59e0b"
        else:
            color = "#dc2626"

        return format_html(
            '<span style="background:{}; color:{}; padding:6px 10px; border-radius:999px; font-weight:800;">{} / 100</span>',
            color,
            "white",
            obj.puntaje_quant
        )

    puntaje_quant_badge.short_description = "Score"

    def activo_coloreado(self, obj):
        if obj.activo:
            return format_html(
                '<span style="color:{}; font-weight:800;">{}</span>',
                "#16a34a",
                "Activo"
            )
        return format_html(
            '<span style="color:{}; font-weight:800;">{}</span>',
            "#dc2626",
            "Inactivo"
        )

    activo_coloreado.short_description = "Estado"

    def destacado_coloreado(self, obj):
        if obj.es_destacado:
            return format_html(
                '<span style="color:{}; font-weight:800;">{}</span>',
                "#f59e0b",
                "★ Destacado"
            )
        return format_html(
            '<span style="color:{}; font-weight:700;">{}</span>',
            "#94a3b8",
            "Normal"
        )

    destacado_coloreado.short_description = "Visibilidad"

   

