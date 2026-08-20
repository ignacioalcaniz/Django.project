from django.db import models


class Producto(models.Model):
    TIPOS_ACTIVO = [
        ("accion", "Acción"),
        ("etf", "ETF"),
        ("crypto", "Criptomoneda"),
        ("indice", "Índice"),
        ("bono", "Bono"),
        ("fondo", "Fondo"),
    ]

    NIVELES_RIESGO = [
        ("bajo", "Bajo"),
        ("medio", "Medio"),
        ("alto", "Alto"),
    ]

    RECOMENDACIONES = [
        ("comprar", "Comprar"),
        ("mantener", "Mantener"),
        ("vender", "Vender"),
        ("observar", "Observar"),
    ]

    MONEDAS = [
        ("USD", "Dólar estadounidense"),
        ("ARS", "Peso argentino"),
        ("EUR", "Euro"),
        ("GBP", "Libra esterlina"),
    ]

    PROVEEDORES_DATOS = [
        ("twelve_data", "Twelve Data"),
    ]

    ESTADOS_SINCRONIZACION = [
        ("pendiente", "Pendiente"),
        ("sincronizado", "Sincronizado"),
        ("error", "Error"),
        ("desactivado", "Desactivado"),
    ]

    # ============================================================
    # IDENTIDAD
    # ============================================================

    nombre = models.CharField(
        max_length=120,
        verbose_name="Nombre del activo",
    )

    simbolo = models.CharField(
        max_length=10,
        default="SINM",
        verbose_name="Símbolo",
    )

    ticker_externo = models.CharField(
        max_length=20,
        blank=True,
        default="",
        verbose_name="Ticker externo",
    )

    descripcion = models.TextField(
        blank=True,
        default="",
        verbose_name="Descripción",
    )

    imagen = models.ImageField(
        upload_to="activos/",
        blank=True,
        null=True,
        verbose_name="Imagen",
    )

    # ============================================================
    # PRECIOS
    # ============================================================

    precio_actual = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="Precio actual",
    )

    precio_objetivo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="Precio objetivo",
    )

    apertura = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="Precio de apertura",
    )

    cierre_anterior = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="Cierre anterior",
    )

    variacion_diaria = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0.00,
        verbose_name="Variación diaria (%)",
    )

    variacion_semanal = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0.00,
        verbose_name="Variación semanal (%)",
    )

    variacion_mensual = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0.00,
        verbose_name="Variación mensual (%)",
    )

    maximo_dia = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="Máximo del día",
    )

    minimo_dia = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="Mínimo del día",
    )

    maximo_52_semanas = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="Máximo 52 semanas",
    )

    minimo_52_semanas = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="Mínimo 52 semanas",
    )

    # ============================================================
    # MERCADO / FUNDAMENTALES
    # ============================================================

    volumen = models.PositiveBigIntegerField(
        default=0,
        verbose_name="Volumen",
    )

    volumen_promedio = models.PositiveBigIntegerField(
        default=0,
        verbose_name="Volumen promedio",
    )

    capitalizacion_mercado = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0.00,
        verbose_name="Capitalización de mercado",
    )

    pe_ratio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name="P/E Ratio",
    )

    eps = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name="EPS",
    )

    dividendo = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0.00,
        verbose_name="Dividendo (%)",
    )

    beta = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0.00,
        verbose_name="Beta",
    )

    # ============================================================
    # CLASIFICACIÓN
    # ============================================================

    sector = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Sector",
    )

    industria = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Industria",
    )

    pais = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="País",
    )

    bolsa = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name="Bolsa",
    )

    moneda = models.CharField(
        max_length=10,
        choices=MONEDAS,
        default="USD",
        verbose_name="Moneda",
    )

    tipo_activo = models.CharField(
        max_length=20,
        choices=TIPOS_ACTIVO,
        default="accion",
        verbose_name="Tipo de activo",
    )

    # ============================================================
    # ANÁLISIS QUANTEDGE
    # ============================================================

    riesgo = models.CharField(
        max_length=10,
        choices=NIVELES_RIESGO,
        default="medio",
        verbose_name="Nivel de riesgo",
    )

    recomendacion = models.CharField(
        max_length=10,
        choices=RECOMENDACIONES,
        default="mantener",
        verbose_name="Recomendación",
    )

    puntaje_quant = models.PositiveIntegerField(
        default=50,
        verbose_name="Puntaje QuantEdge",
    )

    confianza_modelo = models.PositiveIntegerField(
        default=50,
        verbose_name="Confianza del modelo (%)",
    )

    nota_analista = models.TextField(
        blank=True,
        default="",
        verbose_name="Nota del analista",
    )

    tesis_inversion = models.TextField(
        blank=True,
        default="",
        verbose_name="Tesis de inversión",
    )

    # ============================================================
    # MARKET DATA / SINCRONIZACIÓN
    # ============================================================

    proveedor_datos = models.CharField(
        max_length=30,
        choices=PROVEEDORES_DATOS,
        default="twelve_data",
        verbose_name="Proveedor de datos",
    )

    sincronizacion_automatica = models.BooleanField(
        default=True,
        verbose_name="Sincronización automática",
        help_text=(
            "Permite que este activo pueda ser actualizado "
            "automáticamente por tareas programadas."
        ),
    )

    estado_sincronizacion = models.CharField(
        max_length=20,
        choices=ESTADOS_SINCRONIZACION,
        default="pendiente",
        verbose_name="Estado de sincronización",
    )

    fecha_ultimo_intento_sincronizacion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Último intento de sincronización",
    )

    fecha_ultima_sincronizacion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Última sincronización exitosa",
    )

    ultimo_error_sincronizacion = models.TextField(
        blank=True,
        default="",
        verbose_name="Último error de sincronización",
    )

    # ============================================================
    # ESTADO
    # ============================================================

    es_destacado = models.BooleanField(
        default=False,
        verbose_name="Destacado",
    )

    activo = models.BooleanField(
        default=True,
        verbose_name="Activo",
    )

    # ============================================================
    # AUDITORÍA
    # ============================================================

    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación",
    )

    fecha_actualizacion = models.DateTimeField(
        auto_now=True,
        verbose_name="Última actualización",
    )

    fecha_ultima_revision = models.DateField(
        null=True,
        blank=True,
        verbose_name="Última revisión",
    )

    class Meta:
        verbose_name = "Activo"
        verbose_name_plural = "Activos"
        ordering = ["nombre"]

        indexes = [
            models.Index(
                fields=["simbolo"],
                name="qe_producto_simbolo_idx",
            ),
            models.Index(
                fields=["ticker_externo"],
                name="qe_producto_ticker_idx",
            ),
            models.Index(
                fields=[
                    "activo",
                    "sincronizacion_automatica",
                ],
                name="qe_producto_sync_idx",
            ),
        ]

    @property
    def ticker_mercado(self):
        """
        Identificador utilizado para consultar el proveedor externo.

        Si no existe ticker_externo, utiliza el símbolo interno.
        """
        return (
            self.ticker_externo.strip()
            or self.simbolo.strip()
        ).upper()

    @property
    def sincronizacion_correcta(self):
        return (
            self.estado_sincronizacion
            == "sincronizado"
        )

    def __str__(self):
        return f"{self.simbolo} - {self.nombre}"

    