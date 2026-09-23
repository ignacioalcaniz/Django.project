from django.utils import timezone
from rest_framework import serializers

from vistaprevia.models import CotizacionHistorica, Producto


class ProductoSerializer(serializers.ModelSerializer):
    tipo_activo_display = serializers.CharField(
        source="get_tipo_activo_display",
        read_only=True,
    )

    riesgo_display = serializers.CharField(
        source="get_riesgo_display",
        read_only=True,
    )

    recomendacion_display = serializers.CharField(
        source="get_recomendacion_display",
        read_only=True,
    )

    moneda_display = serializers.CharField(
        source="get_moneda_display",
        read_only=True,
    )

    ticker_mercado = serializers.CharField(
        read_only=True,
    )

    score_calculado = serializers.SerializerMethodField()

    class Meta:
        model = Producto

        fields = [
            "id",
            "nombre",
            "simbolo",
            "ticker_externo",
            "ticker_mercado",
            "descripcion",
            "imagen",

            "tipo_activo",
            "tipo_activo_display",
            "sector",
            "industria",
            "pais",
            "bolsa",
            "moneda",
            "moneda_display",

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

            "volumen",
            "volumen_promedio",
            "capitalizacion_mercado",
            "pe_ratio",
            "eps",
            "dividendo",
            "beta",

            "riesgo",
            "riesgo_display",
            "recomendacion",
            "recomendacion_display",

            "puntaje_quant",
            "cobertura_datos_quant",
            "version_score_quant",
            "fecha_ultimo_score_quant",
            "score_calculado",

            "nota_analista",
            "tesis_inversion",

            "proveedor_datos",
            "sincronizacion_automatica",
            "estado_sincronizacion",
            "fecha_ultimo_intento_sincronizacion",
            "fecha_ultima_sincronizacion",

            "es_destacado",
            "activo",

            "fecha_creacion",
            "fecha_actualizacion",
            "fecha_ultima_revision",
        ]

        read_only_fields = [
            "id",
            "ticker_mercado",

            # Datos administrados por sincronización
            "precio_actual",
            "apertura",
            "cierre_anterior",
            "variacion_diaria",
            "maximo_dia",
            "minimo_dia",
            "volumen",
            "bolsa",
            "moneda",
            "proveedor_datos",

            # QuantEdge Scoring Engine
            "recomendacion",
            "puntaje_quant",
            "cobertura_datos_quant",
            "version_score_quant",
            "fecha_ultimo_score_quant",
            "score_calculado",

            # Estado técnico de sincronización
            "estado_sincronizacion",
            "fecha_ultimo_intento_sincronizacion",
            "fecha_ultima_sincronizacion",

            # Auditoría
            "fecha_creacion",
            "fecha_actualizacion",
        ]

    def get_score_calculado(self, obj):
        return obj.fecha_ultimo_score_quant is not None

    def validate(self, attrs):
        instance = self.instance

        if instance is not None:
            if (
                "simbolo" in attrs
                and attrs["simbolo"] != instance.simbolo
            ):
                raise serializers.ValidationError(
                    {
                        "simbolo": (
                            "El símbolo de un activo existente "
                            "no puede modificarse."
                        )
                    }
                )

            if (
                "ticker_externo" in attrs
                and attrs["ticker_externo"]
                != instance.ticker_externo
            ):
                raise serializers.ValidationError(
                    {
                        "ticker_externo": (
                            "El ticker externo de un activo existente "
                            "no puede modificarse."
                        )
                    }
                )

        minimo_52 = attrs.get(
            "minimo_52_semanas",
            getattr(instance, "minimo_52_semanas", None),
        )

        maximo_52 = attrs.get(
            "maximo_52_semanas",
            getattr(instance, "maximo_52_semanas", None),
        )

        if (
            minimo_52 is not None
            and maximo_52 is not None
            and minimo_52 > maximo_52
        ):
            raise serializers.ValidationError(
                {
                    "minimo_52_semanas": (
                        "El mínimo de 52 semanas no puede "
                        "ser mayor que el máximo."
                    )
                }
            )

        return attrs

    def validate_precio_objetivo(self, value):
        if value < 0:
            raise serializers.ValidationError(
                "El precio objetivo no puede ser negativo."
            )

        return value

    def validate_capitalizacion_mercado(self, value):
        if value < 0:
            raise serializers.ValidationError(
                "La capitalización de mercado "
                "no puede ser negativa."
            )

        return value

    def create(self, validated_data):
        simbolo = validated_data.get(
            "simbolo",
            "",
        ).strip().upper()

        ticker_externo = validated_data.get(
            "ticker_externo",
            "",
        ).strip().upper()

        if not simbolo:
            raise serializers.ValidationError(
                {
                    "simbolo": (
                        "El símbolo es obligatorio para "
                        "crear un activo."
                    )
                }
            )

        ticker_efectivo = ticker_externo or simbolo

        duplicado = Producto.objects.filter(
            ticker_externo__iexact=ticker_efectivo
        ).exists()

        if not duplicado:
            duplicado = Producto.objects.filter(
                ticker_externo="",
                simbolo__iexact=ticker_efectivo,
            ).exists()

        if duplicado:
            raise serializers.ValidationError(
                {
                    "simbolo": (
                        "Ya existe un activo con esta "
                        "identidad de mercado."
                    )
                }
            )

        validated_data["simbolo"] = simbolo
        validated_data["ticker_externo"] = ticker_externo

        # Un activo nuevo no se publica hasta disponer
        # de datos de mercado válidos.
        validated_data["activo"] = False

        return Producto.objects.create(**validated_data)

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)

        update_fields = list(validated_data.keys())

        if "fecha_actualizacion" not in update_fields:
            instance.fecha_actualizacion = timezone.now()
            update_fields.append("fecha_actualizacion")

        instance.save(
            update_fields=update_fields
        )

        return instance


class CotizacionHistoricaSerializer(serializers.ModelSerializer):
    simbolo = serializers.CharField(
        source="activo.simbolo",
        read_only=True,
    )

    class Meta:
        model = CotizacionHistorica

        fields = [
            "id",
            "simbolo",
            "fecha_hora",
            "intervalo",
            "apertura",
            "maximo",
            "minimo",
            "cierre",
            "volumen",
            "proveedor",
        ]

        read_only_fields = fields