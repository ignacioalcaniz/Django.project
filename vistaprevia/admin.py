import csv

from django import forms
from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.utils import timezone
from django.utils.html import format_html

from .exceptions import MarketDataError
from .models import Producto
from .services.market_sync import MarketDataSyncService


admin.site.site_header = "QuantEdge Admin | Inteligencia Bursátil"
admin.site.site_title = "QuantEdge"
admin.site.index_title = "Panel de administración de QuantEdge"


class ActualizacionAnalisisForm(forms.Form):
    recomendacion = forms.ChoiceField(
        label="Nueva recomendación",
        choices=[("", "Mantener valor actual")]
        + Producto.RECOMENDACIONES,
        required=False,
    )

    riesgo = forms.ChoiceField(
        label="Nuevo nivel de riesgo",
        choices=[("", "Mantener valor actual")]
        + Producto.NIVELES_RIESGO,
        required=False,
    )

    puntaje_quant = forms.IntegerField(
        label="Puntaje QuantEdge",
        required=False,
        min_value=0,
        max_value=100,
        help_text=(
            "Dejá el campo vacío para mantener "
            "el puntaje actual."
        ),
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
                    "Escribí una observación profesional "
                    "para los activos seleccionados."
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
    list_display = (
        "id",
        "preview_imagen",
        "simbolo_badge",
        "ticker_externo",
        "nombre",
        "tipo_activo_badge",
        "precio_actual",
        "moneda",
        "variacion_coloreada",
        "estado_sincronizacion_badge",
        "fecha_ultima_sincronizacion",
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
        "ticker_externo",
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
        "ultimo_error_sincronizacion",
    )

    list_filter = (
        "tipo_activo",
        "riesgo",
        "recomendacion",
        "moneda",
        "activo",
        "es_destacado",
        "proveedor_datos",
        "sincronizacion_automatica",
        "estado_sincronizacion",
        "sector",
        "industria",
        "pais",
        "bolsa",
        "fecha_ultima_sincronizacion",
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
        "estado_sincronizacion",
        "fecha_ultimo_intento_sincronizacion",
        "fecha_ultima_sincronizacion",
        "ultimo_error_sincronizacion",
        "fecha_creacion",
        "fecha_actualizacion",
    )

    actions = (
        "sincronizar_datos_mercado",
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
                ),
                "description": (
                    "El símbolo identifica al activo dentro de QuantEdge. "
                    "El ticker externo corresponde al identificador utilizado "
                    "por el proveedor de datos de mercado."
                ),
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
            "Datos de mercado",
            {
                "fields": (
                    "precio_actual",
                    "apertura",
                    "cierre_anterior",
                    "maximo_dia",
                    "minimo_dia",
                    "variacion_diaria",
                    "variacion_semanal",
                    "variacion_mensual",
                    "maximo_52_semanas",
                    "minimo_52_semanas",
                    "volumen",
                    "volumen_promedio",
                ),
                "description": (
                    "Estos datos pueden ser actualizados mediante "
                    "el subsistema de Market Data de QuantEdge."
                ),
            },
        ),
        (
            "Valoración fundamental",
            {
                "fields": (
                    "precio_objetivo",
                    "capitalizacion_mercado",
                    "pe_ratio",
                    "eps",
                    "dividendo",
                    "beta",
                )
            },
        ),
        (
            "Integración de Market Data",
            {
                "fields": (
                    "proveedor_datos",
                    "sincronizacion_automatica",
                    "estado_sincronizacion",
                    "fecha_ultimo_intento_sincronizacion",
                    "fecha_ultima_sincronizacion",
                    "ultimo_error_sincronizacion",
                ),
                "description": (
                    "Configuración y estado operativo de la integración "
                    "con proveedores externos de datos financieros."
                ),
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
                ),
                "description": (
                    "Estos campos corresponden a la capa analítica propia "
                    "de QuantEdge y no son reemplazados por el proveedor "
                    "externo de datos."
                ),
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

    # ============================================================
    # MARKET DATA
    # ============================================================

    @admin.action(
        description="Sincronizar datos de mercado seleccionados"
    )
    def sincronizar_datos_mercado(
        self,
        request,
        queryset,
    ):
        try:
            service = MarketDataSyncService()

        except MarketDataError as exc:
            self.message_user(
                request,
                (
                    "No fue posible iniciar el servicio "
                    f"de mercado: {exc}"
                ),
                level=messages.ERROR,
            )
            return

        resultados = service.sincronizar_queryset(
            queryset,
            force=True,
        )

        exitosos = [
            resultado
            for resultado in resultados
            if resultado.success
        ]

        fallidos = [
            resultado
            for resultado in resultados
            if not resultado.success
        ]

        if exitosos:
            self.message_user(
                request,
                (
                    f"{len(exitosos)} activo/s sincronizado/s "
                    "correctamente con el proveedor de mercado."
                ),
                level=messages.SUCCESS,
            )

        for resultado in fallidos:
            self.message_user(
                request,
                (
                    f"{resultado.simbolo}: "
                    f"{resultado.message}"
                ),
                level=messages.WARNING,
            )

        if fallidos:
            self.message_user(
                request,
                (
                    f"{len(fallidos)} activo/s no pudieron "
                    "sincronizarse."
                ),
                level=messages.WARNING,
            )

    # ============================================================
    # PÁGINA INTERMEDIA DE ANÁLISIS
    # ============================================================

    @admin.action(
        description="Actualizar análisis QuantEdge con confirmación"
    )
    def actualizar_analisis_intermedio(
        self,
        request,
        queryset,
    ):
        selected_ids = request.POST.getlist(
            helpers.ACTION_CHECKBOX_NAME
        )

        if "apply" in request.POST:
            form = ActualizacionAnalisisForm(
                request.POST
            )

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
                    datos_actualizacion[
                        "recomendacion"
                    ] = recomendacion

                if riesgo:
                    datos_actualizacion[
                        "riesgo"
                    ] = riesgo

                if puntaje_quant is not None:
                    datos_actualizacion[
                        "puntaje_quant"
                    ] = puntaje_quant

                if confianza_modelo is not None:
                    datos_actualizacion[
                        "confianza_modelo"
                    ] = confianza_modelo

                if nota_analista:
                    datos_actualizacion[
                        "nota_analista"
                    ] = nota_analista.strip()

                if form.cleaned_data.get(
                    "actualizar_fecha_revision"
                ):
                    datos_actualizacion[
                        "fecha_ultima_revision"
                    ] = timezone.localdate()

                actualizados = queryset.update(
                    **datos_actualizacion
                )

                self.message_user(
                    request,
                    (
                        f"{actualizados} activo/s "
                        "actualizado/s correctamente mediante "
                        "la página intermedia de análisis."
                    ),
                    level=messages.SUCCESS,
                )

                return redirect(
                    request.get_full_path()
                )

        else:
            form = ActualizacionAnalisisForm()

        context = {
            **self.admin_site.each_context(request),
            "title": "Actualizar análisis QuantEdge",
            "subtitle": (
                "Configurá los nuevos valores antes "
                "de ejecutar la actualización masiva."
            ),
            "form": form,
            "queryset": queryset,
            "selected_ids": selected_ids,
            "action_checkbox_name": (
                helpers.ACTION_CHECKBOX_NAME
            ),
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

    # ============================================================
    # ACCIONES OPERATIVAS
    # ============================================================

    @admin.action(
        description="Marcar seleccionados como destacados"
    )
    def marcar_como_destacados(
        self,
        request,
        queryset,
    ):
        updated = queryset.update(
            es_destacado=True
        )

        self.message_user(
            request,
            (
                f"{updated} activo/s marcado/s "
                "como destacados."
            ),
        )

    @admin.action(
        description="Quitar destacados"
    )
    def quitar_destacados(
        self,
        request,
        queryset,
    ):
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
    def activar_activos(
        self,
        request,
        queryset,
    ):
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
    def desactivar_activos(
        self,
        request,
        queryset,
    ):
        updated = queryset.update(
            activo=False
        )

        self.message_user(
            request,
            f"{updated} activo/s desactivado/s.",
        )

    # ============================================================
    # RECOMENDACIONES
    # ============================================================

    @admin.action(
        description="Cambiar recomendación a Comprar"
    )
    def recomendar_comprar(
        self,
        request,
        queryset,
    ):
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
    def recomendar_mantener(
        self,
        request,
        queryset,
    ):
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
    def recomendar_observar(
        self,
        request,
        queryset,
    ):
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
    def recomendar_vender(
        self,
        request,
        queryset,
    ):
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

    # ============================================================
    # RIESGO
    # ============================================================

    @admin.action(
        description="Cambiar riesgo a Bajo"
    )
    def riesgo_bajo(
        self,
        request,
        queryset,
    ):
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
    def riesgo_medio(
        self,
        request,
        queryset,
    ):
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
    def riesgo_alto(
        self,
        request,
        queryset,
    ):
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

    # ============================================================
    # EXPORTACIÓN
    # ============================================================

    @admin.action(
        description="Exportar activos seleccionados a CSV"
    )
    def exportar_activos_csv(
        self,
        request,
        queryset,
    ):
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
                "Proveedor",
                "Estado sincronización",
                "Última sincronización",
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
                    activo.get_proveedor_datos_display(),
                    activo.get_estado_sincronizacion_display(),
                    activo.fecha_ultima_sincronizacion,
                    activo.get_riesgo_display(),
                    activo.get_recomendacion_display(),
                    activo.puntaje_quant,
                    activo.confianza_modelo,
                    activo.activo,
                    activo.es_destacado,
                ]
            )

        return response

    # ============================================================
    # REPRESENTACIÓN VISUAL
    # ============================================================

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
            '<span class="qe-admin-muted">{}</span>',
            "Sin imagen",
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

        valor_formateado = f"{valor:.2f}%"

        if valor > 0:
            valor_formateado = (
                f"+{valor_formateado}"
            )

            return format_html(
                '<span class="qe-positive">{}</span>',
                valor_formateado,
            )

        if valor < 0:
            return format_html(
                '<span class="qe-negative">{}</span>',
                valor_formateado,
            )

        return format_html(
            '<span class="qe-neutral">{}</span>',
            valor_formateado,
        )

    variacion_coloreada.short_description = "Variación"

    def estado_sincronizacion_badge(self, obj):
        clases = {
            "pendiente": "qe-warning",
            "sincronizado": "qe-positive",
            "error": "qe-negative",
            "desactivado": "qe-neutral",
        }

        return format_html(
            '<span class="{}">{}</span>',
            clases.get(
                obj.estado_sincronizacion,
                "qe-neutral",
            ),
            obj.get_estado_sincronizacion_display(),
        )

    estado_sincronizacion_badge.short_description = (
        "Market Data"
    )

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

    def recomendacion_coloreada(
        self,
        obj,
    ):
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
                '<span class="qe-positive">{}</span>',
                "Activo",
            )

        return format_html(
            '<span class="qe-negative">{}</span>',
            "Inactivo",
        )

    activo_coloreado.short_description = "Estado"

    def destacado_coloreado(self, obj):
        if obj.es_destacado:
            return format_html(
                '<span class="qe-warning">{}</span>',
                "★ Destacado",
            )

        return format_html(
            '<span class="qe-neutral">{}</span>',
            "Normal",
        )

    destacado_coloreado.short_description = "Visibilidad"

   

