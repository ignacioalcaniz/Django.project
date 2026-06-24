from django.contrib.auth.models import User
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import (
    PerfilUsuario,
    InversionSimulada,
    ConsultaIA,
    ActivoFavorito,
    Notificacion,
)


@receiver(post_save, sender=User)
def crear_perfil_usuario(sender, instance, created, **kwargs):
    if created:
        PerfilUsuario.objects.get_or_create(
            usuario=instance,
            defaults={
                "nombre_completo": f"{instance.first_name} {instance.last_name}".strip()
            }
        )


@receiver(post_save, sender=InversionSimulada)
def notificar_compra_simulada(sender, instance, created, **kwargs):
    if created:
        Notificacion.objects.create(
            usuario=instance.usuario,
            tipo="compra",
            titulo="Compra simulada realizada",
            mensaje=(
                f"Compraste {instance.cantidad} acción/es de "
                f"{instance.activo.simbolo} a USD {instance.precio_compra}."
            ),
        )


@receiver(post_save, sender=ConsultaIA)
def notificar_analisis_ia(sender, instance, created, **kwargs):
    if created:
        Notificacion.objects.create(
            usuario=instance.usuario,
            tipo="ia",
            titulo="Nuevo análisis IA generado",
            mensaje=f"QuantEdge generó un análisis para {instance.activo.simbolo}.",
        )


@receiver(post_save, sender=ActivoFavorito)
def notificar_activo_favorito(sender, instance, created, **kwargs):
    if created:
        Notificacion.objects.create(
            usuario=instance.usuario,
            tipo="favorito",
            titulo="Activo agregado a watchlist",
            mensaje=f"{instance.activo.simbolo} fue agregado a tu watchlist.",
        )


@receiver(post_delete, sender=ActivoFavorito)
def notificar_activo_favorito_eliminado(sender, instance, **kwargs):
    Notificacion.objects.create(
        usuario=instance.usuario,
        tipo="favorito",
        titulo="Activo eliminado de watchlist",
        mensaje=f"{instance.activo.simbolo} fue eliminado de tu watchlist.",
    )