import uuid
from django.conf import settings
from django.db import models
from django.urls import reverse


class OrdenPago(models.Model):
    class Estado(models.TextChoices):
        CREATED = "CREATED", "Creada"
        PENDING = "PENDING", "Pendiente"
        ACTION_REQUIRED = "ACTION_REQUIRED", "Accion requerida"
        APPROVED = "APPROVED", "Acreditada (prueba)"
        REJECTED = "REJECTED", "Rechazada"
        CANCELLED = "CANCELLED", "Cancelada"
        ERROR = "ERROR", "Error recuperable"
        REFUNDED = "REFUNDED", "Reembolsada"
        PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED", "Reembolso parcial"
        REVIEW_REQUIRED = "REVIEW_REQUIRED", "Revision requerida"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    activo = models.ForeignKey("vistaprevia.Producto", on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField()
    nombre_snapshot = models.CharField(max_length=120)
    simbolo_snapshot = models.CharField(max_length=10)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    moneda_activo = models.CharField(max_length=3)
    importe_demo = models.DecimalField(max_digits=12, decimal_places=2)
    moneda_cobro = models.CharField(max_length=3, default="ARS")
    estado = models.CharField(max_length=24, choices=Estado.choices, default=Estado.CREATED)
    environment = models.CharField(max_length=10, default="test")
    submission_key = models.UUIDField(unique=True)
    idempotency_key = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    mp_order_id = models.CharField(max_length=64, unique=True, null=True, blank=True)
    checkout_url = models.URLField(max_length=1000, blank=True)
    # Immutable, minimal outbound payload: demo item and return URLs; no payer/cards.
    checkout_payload = models.JSONField(default=dict)
    mp_status = models.CharField(max_length=64, blank=True)
    mp_status_detail = models.CharField(max_length=128, blank=True)
    mp_user_id = models.CharField(max_length=64, blank=True)
    mp_application_id = models.CharField(max_length=64, blank=True)
    # Epoch microseconds avoids mixing aware provider timestamps with USE_TZ=False.
    mp_updated_us = models.BigIntegerField(null=True, blank=True)
    inversion = models.OneToOneField("usuarios.InversionSimulada", on_delete=models.PROTECT,
                                    null=True, blank=True, related_name="orden_pago")
    creada = models.DateTimeField(auto_now_add=True)
    actualizada = models.DateTimeField(auto_now=True)
    aprobada = models.DateTimeField(null=True, blank=True)
    reembolsada = models.DateTimeField(null=True, blank=True)
    ultimo_intento = models.DateTimeField(null=True, blank=True)
    ultimo_error = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ["-creada"]
        indexes = [models.Index(fields=["estado", "actualizada"], name="pago_estado_fecha"),
                   models.Index(fields=["usuario", "creada"], name="pago_usuario_fecha")]
        constraints = [
            models.CheckConstraint(condition=models.Q(cantidad__gte=1, cantidad__lte=100000), name="pago_cantidad_valida"),
            models.CheckConstraint(condition=models.Q(precio_unitario__gt=0), name="pago_precio_positivo"),
            models.CheckConstraint(condition=models.Q(importe_demo__gt=0), name="pago_demo_positivo"),
            models.CheckConstraint(condition=models.Q(moneda_cobro="ARS", environment="test"), name="pago_solo_demo_ars"),
        ]

    @property
    def total_financiero(self):
        return self.cantidad * self.precio_unitario

    @property
    def puede_iniciar(self):
        return self.estado in {self.Estado.CREATED, self.Estado.PENDING, self.Estado.ERROR}

    def get_absolute_url(self):
        return reverse("pagos:orden_detalle", kwargs={"pk": self.pk})

    def __str__(self):
        return str(self.pk)


class PagoProveedor(models.Model):
    orden = models.ForeignKey(OrdenPago, on_delete=models.PROTECT, related_name="transacciones")
    external_id = models.CharField(max_length=64, unique=True)
    estado = models.CharField(max_length=64)
    detalle = models.CharField(max_length=128, blank=True)
    importe = models.DecimalField(max_digits=12, decimal_places=2)
    moneda = models.CharField(max_length=3)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(importe__gte=0), name="proveedor_importe_valido")]


class EventoPago(models.Model):
    orden = models.ForeignKey(OrdenPago, on_delete=models.PROTECT, related_name="eventos")
    origen = models.CharField(max_length=20)
    resultado = models.CharField(max_length=64)
    estado_anterior = models.CharField(max_length=24, blank=True)
    estado_nuevo = models.CharField(max_length=24, blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado"]
