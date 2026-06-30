def admin_metrics(request):
    if not request.path.startswith("/admin"):
        return {}

    try:
        from django.contrib.auth.models import User
        from django.contrib.admin.models import LogEntry
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
            "admin_contactos_pendientes": ConsultaContacto.objects.filter(estado="pendiente").count(),
            "admin_top_activos": Producto.objects.filter(activo=True).order_by("-puntaje_quant")[:5],
            "admin_ultimas_consultas_ia": ConsultaIA.objects.select_related("usuario", "activo").order_by("-fecha_creacion")[:5],
            "admin_ultimas_notificaciones": Notificacion.objects.select_related("usuario").order_by("-fecha_creacion")[:5],
            "admin_logs_recientes": LogEntry.objects.select_related("user", "content_type").order_by("-action_time")[:6],
        }

    except Exception:
        return {}