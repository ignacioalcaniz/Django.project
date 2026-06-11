from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from vistaprevia.models import Producto


class PerfilUsuario(models.Model):
    PERFILES_INVERSOR = [
        ("conservador", "Conservador"),
        ("moderado", "Moderado"),
        ("agresivo", "Agresivo"),
    ]

    usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="perfil",
        verbose_name="Usuario"
    )
    foto = models.ImageField(upload_to="perfiles/", blank=True, null=True, verbose_name="Foto de perfil")
    nombre_completo = models.CharField(max_length=150, blank=True, default="", verbose_name="Nombre completo")
    telefono = models.CharField(max_length=30, blank=True, default="", verbose_name="Teléfono")
    pais = models.CharField(max_length=80, blank=True, default="Argentina", verbose_name="País")
    perfil_inversor = models.CharField(
        max_length=20,
        choices=PERFILES_INVERSOR,
        default="moderado",
        verbose_name="Perfil inversor"
    )
    capital_demo = models.DecimalField(max_digits=12, decimal_places=2, default=25000.00, verbose_name="Capital demo")
    biografia = models.TextField(blank=True, default="", verbose_name="Biografía")
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Última actualización")

    class Meta:
        verbose_name = "Perfil de usuario"
        verbose_name_plural = "Perfiles de usuarios"

    def __str__(self):
        return f"Perfil de {self.usuario.username}"


class InversionSimulada(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name="inversiones_simuladas")
    activo = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="inversiones_simuladas")
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

    def valor_actual(self):
        return self.cantidad * self.activo.precio_actual

    def ganancia_perdida(self):
        return self.valor_actual() - self.total_invertido()

    def rentabilidad_porcentual(self):
        total = self.total_invertido()

        if total == 0:
            return Decimal("0.00")

        return (self.ganancia_perdida() / total) * Decimal("100")

    def resultado_es_positivo(self):
        return self.ganancia_perdida() >= 0


class ConsultaIA(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name="consultas_ia")
    activo = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="consultas_ia")
    pregunta = models.TextField(blank=True, default="", verbose_name="Pregunta")
    respuesta = models.TextField(verbose_name="Respuesta IA")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de consulta")

    class Meta:
        verbose_name = "Consulta IA"
        verbose_name_plural = "Consultas IA"
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"IA - {self.usuario.username} - {self.activo.simbolo}"


class ActivoFavorito(models.Model):
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="activos_favoritos",
        verbose_name="Usuario"
    )
    activo = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name="usuarios_favoritos",
        verbose_name="Activo"
    )
    fecha_agregado = models.DateTimeField(auto_now_add=True, verbose_name="Fecha agregado")

    class Meta:
        verbose_name = "Activo favorito"
        verbose_name_plural = "Activos favoritos"
        ordering = ["-fecha_agregado"]
        unique_together = ("usuario", "activo")

    def __str__(self):
        return f"{self.usuario.username} - {self.activo.simbolo}"
