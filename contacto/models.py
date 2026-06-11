from django.db import models
from django.contrib.auth.models import User


class ConsultaContacto(models.Model):
    CATEGORIAS = [
        ("soporte", "Soporte técnico"),
        ("premium", "Plan premium"),
        ("asesoramiento", "Asesoramiento financiero"),
        ("problema", "Problema técnico"),
        ("otro", "Otro"),
    ]

    ESTADOS = [
        ("pendiente", "Pendiente"),
        ("respondido", "Respondido"),
        ("cerrado", "Cerrado"),
    ]

    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="consultas_contacto",
        verbose_name="Usuario"
    )
    nombre = models.CharField(max_length=120, verbose_name="Nombre")
    email = models.EmailField(verbose_name="Email")
    categoria = models.CharField(max_length=20, choices=CATEGORIAS, default="soporte")
    asunto = models.CharField(max_length=150, verbose_name="Asunto")
    mensaje = models.TextField(verbose_name="Mensaje")
    estado = models.CharField(max_length=20, choices=ESTADOS, default="pendiente")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")

    class Meta:
        verbose_name = "Consulta de contacto"
        verbose_name_plural = "Consultas de contacto"
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"{self.nombre} - {self.asunto}"
