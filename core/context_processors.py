SEO_PAGES = {
    "home": (
        "QuantEdge | Inversión asistida por IA",
        "Explorá activos financieros, compará indicadores y simulá inversiones con las herramientas de análisis de QuantEdge.",
    ),
    "ranking_activos": (
        "Ranking de activos | QuantEdge",
        "Consultá el ranking de activos financieros según su puntaje QuantEdge y la cobertura de sus datos cuantitativos.",
    ),
    "comparador_activos": (
        "Comparador de activos | QuantEdge",
        "Compará activos financieros, sus indicadores, niveles de riesgo y puntajes cuantitativos en QuantEdge.",
    ),
    "contacto": (
        "Contacto | QuantEdge",
        "Contactá al equipo de QuantEdge para enviar consultas sobre la plataforma y sus herramientas de análisis financiero.",
    ),
}


def seo(request):
    """Metadata without database queries; only public content is indexable."""
    match = request.resolver_match
    url_name = match.url_name if match else None
    title, description = SEO_PAGES.get(url_name, (
        "QuantEdge",
        "QuantEdge, plataforma de simulación y análisis de inversiones financieras.",
    ))
    public_page = (
        match is not None
        and not match.namespace
        and url_name in (*SEO_PAGES, "activo_detalle")
    )
    comparison = url_name == "comparador_activos" and any(
        key in request.GET for key in ("activo_1", "activo_2")
    )
    return {
        "seo_title": title,
        "seo_description": description,
        "canonical_url": request.build_absolute_uri(request.path),
        "seo_robots": "index, follow" if public_page and not comparison else "noindex, follow",
        "seo_type": "website",
        "seo_image_url": None,
    }


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
