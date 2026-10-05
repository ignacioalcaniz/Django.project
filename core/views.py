from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_safe
from vistaprevia.models import Producto


@require_safe
def robots(request):
    return render(request, "robots.txt", {
        "sitemap_url": request.build_absolute_uri(reverse("sitemap")),
    }, content_type="text/plain; charset=utf-8")


def home(request):
    activos_destacados = Producto.objects.filter(
        activo=True
    ).order_by(
        "-es_destacado",
        "-puntaje_quant",
        "nombre"
    )[:3]

    return render(request, "core/home.html", {
        "activos_destacados": activos_destacados
    })
