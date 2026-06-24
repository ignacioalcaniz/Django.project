def admin_metrics(request):
    if not request.path.startswith("/admin"):
        return {}

    try:
        from django.contrib.auth.models import User
        from vistaprevia.models import Producto
        from usuarios.models import InversionSimulada, ConsultaIA, ActivoFavorito, Notificacion
        from contacto.models import ConsultaContacto

        return {
            "admin_total_usuarios": User.objects.count(),
            "admin_total_activos": Producto.objects.count(),
            "admin_activos_activos": Producto.objects.filter(activo=True).count(),
            "admin_total_inversiones": InversionSimulada.objects.count(),
            "admin_total_consultas_ia": ConsultaIA.objects.count(),
            "admin_total_favoritos": ActivoFavorito.objects.count(),
            "admin_notificaciones_no_leidas": Notificacion.objects.filter(leida=False).count(),
            "admin_total_contactos": ConsultaContacto.objects.count(),
        }

    except Exception:
        return {}