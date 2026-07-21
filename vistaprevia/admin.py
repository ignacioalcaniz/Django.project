import csv

from django import forms
from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.utils import timezone
from django.utils.html import format_html

from .models import Producto


admin.site.site_header = "QuantEdge Admin | Inteligencia Bursátil"
admin.site.site_title = "QuantEdge"
admin.site.index_title = "Panel de administración de QuantEdge"


class ActualizacionAnalisisForm(forms.Form):
    recomendacion = forms.ChoiceField(
        label="Nueva recomendación",
        choices=[("", "Mantener valor actual")] + Producto.RECOMENDACIONES,
        required=False,
    )

    riesgo = forms.ChoiceField(
        label="Nuevo nivel de riesgo",
        choices=[("", "Mantener valor actual")] + Producto.NIVELES_RIESGO,
        required=False,
    )

    puntaje_quant = forms.IntegerField(
        label="Puntaje QuantEdge",
        required=False,
        min_value=0,
        max_value=100,
        help_text="Dejá el campo vacío para mantener el puntaje actual.",
    )

    confianza_modelo = forms.IntegerField(
        label="Confianza del modelo",
        required=False,
        min_value=0,
        max_value=100,
        help_text="Porcentaje entre 0 y 100.",
    )

    nota_analista = forms.CharField(
        label="Nota del analista",
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 5,
                "placeholder": (
                    "Escribí una observación profesional para los "
                    "activos seleccionados."
                ),
            }
        ),
    )

    actualizar_fecha_revision = forms.BooleanField(
        label="Registrar la fecha de revisión de hoy",
        required=False,
        initial=True,
    )

    confirmar = forms.BooleanField(
        label="Confirmo la actualización masiva",
        required=True,
    )

    def clean(self):
        cleaned_data = super().clean()

        campos_actualizables = [
            cleaned_data.get("recomendacion"),
            cleaned_data.get("riesgo"),
            cleaned_data.get("puntaje_quant"),
            cleaned_data.get("confianza_modelo"),
            cleaned_data.get("nota_analista"),
            cleaned_data.get("actualizar_fecha_revision"),
        ]

        if not any(
            valor not in ("", None, False)
            for valor in campos_actualizables
        ):
            raise forms.ValidationError(
                "Debés seleccionar al menos un dato para actualizar."
            )

        return cleaned_data


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    change_list_template = "admin/vistaprevia/producto/change_list.html"

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

    list_editable = (
        "precio_actual",
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

    ordering = (
        "-puntaje_quant",
        "nombre",
    )

    list_per_page = 15
    save_on_top = True
    empty_value_display = "Sin dato"

    readonly_fields = (
        "preview_imagen",
        "fecha_creacion",
        "fecha_actualizacion",
    )

    actions = (
        "actualizar_analisis_intermedio",
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
        "exportar_activos_csv",
    )

    fieldsets = (
        (
            "Identidad del activo",
            {
                "fields": (
                    "nombre",
                    "simbolo",
                    "ticker_externo",
                    "descripcion",
                )
            },
        ),
        (
            "Imagen corporativa",
            {
                "fields": (
                    "imagen",
                    "preview_imagen",
                )
            },
        ),
        (
            "Clasificación de mercado",
            {
                "fields": (
                    "tipo_activo",
                    "sector",
                    "industria",
                    "pais",
                    "bolsa",
                    "moneda",
                )
            },
        ),
        (
            "Precios y variaciones",
            {
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
            },
        ),
        (
            "Volumen y valoración",
            {
                "fields": (
                    "volumen",
                    "volumen_promedio",
                    "capitalizacion_mercado",
                    "pe_ratio",
                    "eps",
                    "dividendo",
                    "beta",
                )
            },
        ),
        (
            "Análisis QuantEdge",
            {
                "fields": (
                    "riesgo",
                    "recomendacion",
                    "puntaje_quant",
                    "confianza_modelo",
                    "nota_analista",
                    "tesis_inversion",
                    "fecha_ultima_revision",
                )
            },
        ),
        (
            "Estado operativo",
            {
                "fields": (
                    "activo",
                    "es_destacado",
                )
            },
        ),
        (
            "Auditoría",
            {
                "fields": (
                    "fecha_creacion",
                    "fecha_actualizacion",
                )
            },
        ),
    )

    @admin.action(
        description="Actualizar análisis QuantEdge con confirmación"
    )
    def actualizar_analisis_intermedio(self, request, queryset):
        selected_ids = request.POST.getlist(
            helpers.ACTION_CHECKBOX_NAME
        )

        if "apply" in request.POST:
            form = ActualizacionAnalisisForm(request.POST)

            if form.is_valid():
                datos_actualizacion = {}

                recomendacion = form.cleaned_data.get(
                    "recomendacion"
                )

                riesgo = form.cleaned_data.get(
                    "riesgo"
                )

                puntaje_quant = form.cleaned_data.get(
                    "puntaje_quant"
                )

                confianza_modelo = form.cleaned_data.get(
                    "confianza_modelo"
                )

                nota_analista = form.cleaned_data.get(
                    "nota_analista"
                )

                if recomendacion:
                    datos_actualizacion["recomendacion"] = (
                        recomendacion
                    )

                if riesgo:
                    datos_actualizacion["riesgo"] = riesgo

                if puntaje_quant is not None:
                    datos_actualizacion["puntaje_quant"] = (
                        puntaje_quant
                    )

                if confianza_modelo is not None:
                    datos_actualizacion["confianza_modelo"] = (
                        confianza_modelo
                    )

                if nota_analista:
                    datos_actualizacion["nota_analista"] = (
                        nota_analista.strip()
                    )

                if form.cleaned_data.get(
                    "actualizar_fecha_revision"
                ):
                    datos_actualizacion["fecha_ultima_revision"] = (
                        timezone.localdate()
                    )

                actualizados = queryset.update(
                    **datos_actualizacion
                )

                self.message_user(
                    request,
                    (
                        f"{actualizados} activo/s actualizado/s "
                        "correctamente mediante la página "
                        "intermedia de análisis."
                    ),
                    level=messages.SUCCESS,
                )

                return redirect(request.get_full_path())
        else:
            form = ActualizacionAnalisisForm()

        context = {
            **self.admin_site.each_context(request),
            "title": "Actualizar análisis QuantEdge",
            "subtitle": (
                "Configurá los nuevos valores antes de ejecutar "
                "la actualización masiva."
            ),
            "form": form,
            "queryset": queryset,
            "selected_ids": selected_ids,
            "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
            "opts": self.model._meta,
            "media": self.media + form.media,
        }

        return TemplateResponse(
            request,
            (
                "admin/vistaprevia/producto/"
                "actualizar_analisis_intermedio.html"
            ),
            context,
        )

    @admin.action(
        description="Marcar seleccionados como destacados"
    )
    def marcar_como_destacados(self, request, queryset):
        updated = queryset.update(
            es_destacado=True
        )

        self.message_user(
            request,
            f"{updated} activo/s marcado/s como destacados.",
        )

    @admin.action(
        description="Quitar destacados"
    )
    def quitar_destacados(self, request, queryset):
        updated = queryset.update(
            es_destacado=False
        )

        self.message_user(
            request,
            (
                f"{updated} activo/s dejaron "
                "de estar destacados."
            ),
        )

    @admin.action(
        description="Activar activos"
    )
    def activar_activos(self, request, queryset):
        updated = queryset.update(
            activo=True
        )

        self.message_user(
            request,
            f"{updated} activo/s activado/s.",
        )

    @admin.action(
        description="Desactivar activos"
    )
    def desactivar_activos(self, request, queryset):
        updated = queryset.update(
            activo=False
        )

        self.message_user(
            request,
            f"{updated} activo/s desactivado/s.",
        )

    @admin.action(
        description="Cambiar recomendación a Comprar"
    )
    def recomendar_comprar(self, request, queryset):
        updated = queryset.update(
            recomendacion="comprar"
        )

        self.message_user(
            request,
            (
                f"{updated} activo/s "
                "actualizado/s a Comprar."
            ),
        )

    @admin.action(
        description="Cambiar recomendación a Mantener"
    )
    def recomendar_mantener(self, request, queryset):
        updated = queryset.update(
            recomendacion="mantener"
        )

        self.message_user(
            request,
            (
                f"{updated} activo/s "
                "actualizado/s a Mantener."
            ),
        )

    @admin.action(
        description="Cambiar recomendación a Observar"
    )
    def recomendar_observar(self, request, queryset):
        updated = queryset.update(
            recomendacion="observar"
        )

        self.message_user(
            request,
            (
                f"{updated} activo/s "
                "actualizado/s a Observar."
            ),
        )

    @admin.action(
        description="Cambiar recomendación a Vender"
    )
    def recomendar_vender(self, request, queryset):
        updated = queryset.update(
            recomendacion="vender"
        )

        self.message_user(
            request,
            (
                f"{updated} activo/s "
                "actualizado/s a Vender."
            ),
        )

    @admin.action(
        description="Cambiar riesgo a Bajo"
    )
    def riesgo_bajo(self, request, queryset):
        updated = queryset.update(
            riesgo="bajo"
        )

        self.message_user(
            request,
            (
                f"{updated} activo/s "
                "actualizado/s a riesgo Bajo."
            ),
        )

    @admin.action(
        description="Cambiar riesgo a Medio"
    )
    def riesgo_medio(self, request, queryset):
        updated = queryset.update(
            riesgo="medio"
        )

        self.message_user(
            request,
            (
                f"{updated} activo/s "
                "actualizado/s a riesgo Medio."
            ),
        )

    @admin.action(
        description="Cambiar riesgo a Alto"
    )
    def riesgo_alto(self, request, queryset):
        updated = queryset.update(
            riesgo="alto"
        )

        self.message_user(
            request,
            (
                f"{updated} activo/s "
                "actualizado/s a riesgo Alto."
            ),
        )

    @admin.action(
        description="Exportar activos seleccionados a CSV"
    )
    def exportar_activos_csv(self, request, queryset):
        response = HttpResponse(
            content_type="text/csv"
        )

        response["Content-Disposition"] = (
            'attachment; filename="quantedge_activos.csv"'
        )

        writer = csv.writer(response)

        writer.writerow(
            [
                "ID",
                "Nombre",
                "Símbolo",
                "Ticker externo",
                "Tipo",
                "Sector",
                "Industria",
                "País",
                "Bolsa",
                "Precio actual",
                "Moneda",
                "Variación diaria",
                "Variación semanal",
                "Variación mensual",
                "Riesgo",
                "Recomendación",
                "Score",
                "Confianza modelo",
                "Activo",
                "Destacado",
            ]
        )

        for activo in queryset:
            writer.writerow(
                [
                    activo.id,
                    activo.nombre,
                    activo.simbolo,
                    activo.ticker_externo,
                    activo.get_tipo_activo_display(),
                    activo.sector,
                    activo.industria,
                    activo.pais,
                    activo.bolsa,
                    activo.precio_actual,
                    activo.moneda,
                    activo.variacion_diaria,
                    activo.variacion_semanal,
                    activo.variacion_mensual,
                    activo.get_riesgo_display(),
                    activo.get_recomendacion_display(),
                    activo.puntaje_quant,
                    activo.confianza_modelo,
                    activo.activo,
                    activo.es_destacado,
                ]
            )

        return response

    def preview_imagen(self, obj):
        if obj and obj.imagen:
            return format_html(
                (
                    '<img src="{}" width="58" height="58" '
                    'style="border-radius:12px; '
                    'object-fit:cover; '
                    'border:2px solid #1e293b; '
                    'box-shadow:0 4px 10px '
                    'rgba(0,0,0,.18);" />'
                ),
                obj.imagen.url,
            )

        return format_html(
            '<span class="qe-admin-muted">Sin imagen</span>'
        )

    preview_imagen.short_description = "Imagen"

    def simbolo_badge(self, obj):
        return format_html(
            '<span class="qe-badge-dark">{}</span>',
            obj.simbolo,
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
            (
                '<span style="background:{};" '
                'class="qe-badge-white">{}</span>'
            ),
            colores.get(
                obj.tipo_activo,
                "#334155",
            ),
            obj.get_tipo_activo_display(),
        )

    tipo_activo_badge.short_description = "Tipo"

    def variacion_coloreada(self, obj):
        valor = float(
            obj.variacion_diaria or 0
        )

        if valor > 0:
            return format_html(
                '<span class="qe-positive">+{:.2f}%</span>',
                valor,
            )

        if valor < 0:
            return format_html(
                '<span class="qe-negative">{:.2f}%</span>',
                valor,
            )

        return format_html(
            '<span class="qe-neutral">{:.2f}%</span>',
            valor,
        )

    variacion_coloreada.short_description = "Variación"

    def riesgo_coloreado(self, obj):
        clases = {
            "bajo": "qe-positive",
            "medio": "qe-warning",
            "alto": "qe-negative",
        }

        return format_html(
            '<span class="{}">{}</span>',
            clases.get(
                obj.riesgo,
                "qe-neutral",
            ),
            obj.get_riesgo_display(),
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
            clases.get(
                obj.recomendacion,
                "qe-neutral",
            ),
            obj.get_recomendacion_display(),
        )

    recomendacion_coloreada.short_description = (
        "Recomendación"
    )

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
            obj.puntaje_quant,
        )

    puntaje_quant_badge.short_description = "Score"

    def activo_coloreado(self, obj):
        if obj.activo:
            return format_html(
                '<span class="qe-positive">Activo</span>'
            )

        return format_html(
            '<span class="qe-negative">Inactivo</span>'
        )

    activo_coloreado.short_description = "Estado"

    def destacado_coloreado(self, obj):
        if obj.es_destacado:
            return format_html(
                (
                    '<span class="qe-warning">'
                    "★ Destacado"
                    "</span>"
                )
            )

        return format_html(
            '<span class="qe-neutral">Normal</span>'
        )

    destacado_coloreado.short_description = "Visibilidad"

   

