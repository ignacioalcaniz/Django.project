from django.db import models
from django.contrib.auth.models import User
from vistaprevia.models import Producto


class InversionSimulada(models.Model):
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="inversiones_simuladas",
        verbose_name="Usuario"
    )
    activo = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name="inversiones_simuladas",
        verbose_name="Activo"
    )
    cantidad = models.PositiveIntegerField(default=1, verbose_name="Cantidad")
    precio_compra = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Precio de compra")
    fecha_compra = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de compra")
    activa = models.BooleanField(default=True, verbose_name="Activa")

    class Meta:
        verbose_name = "Inversión simulada"
        verbose_name_plural = "Inversiones simuladas"
        ordering = ["-fecha_compra"]

    def __str__(self):
        return f"{self.usuario.username} - {self.activo.simbolo}"

    def total_invertido(self):
        return self.cantidad * self.precio_compra


class ConsultaIA(models.Model):
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="consultas_ia",
        verbose_name="Usuario"
    )
    activo = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name="consultas_ia",
        verbose_name="Activo"
    )
    pregunta = models.TextField(blank=True, default="", verbose_name="Pregunta")
    respuesta = models.TextField(verbose_name="Respuesta IA")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de consulta")

    class Meta:
        verbose_name = "Consulta IA"
        verbose_name_plural = "Consultas IA"
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"IA - {self.usuario.username} - {self.activo.simbolo}"
