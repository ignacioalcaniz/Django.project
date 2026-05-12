from django.shortcuts import render
from vistaprevia.models import Producto


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