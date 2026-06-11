from django.shortcuts import render
from django.views.generic import DetailView
from .models import Producto
from usuarios.models import ActivoFavorito


class ActivoDetalleView(DetailView):
    model = Producto
    template_name = "vistaprevia/activo_detalle.html"
    context_object_name = "activo"

    def get_queryset(self):
        return Producto.objects.filter(activo=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        activo = self.object

        context["metricas"] = [
            ("Capitalización", activo.capitalizacion_mercado),
            ("Volumen", activo.volumen),
            ("Volumen promedio", activo.volumen_promedio),
            ("P/E Ratio", activo.pe_ratio),
            ("EPS", activo.eps),
            ("Beta", activo.beta),
            ("Dividendo", activo.dividendo),
        ]

        if self.request.user.is_authenticated:
            context["es_favorito"] = ActivoFavorito.objects.filter(
                usuario=self.request.user,
                activo=activo
            ).exists()
        else:
            context["es_favorito"] = False

        return context


def comparar_activos(request):
    activos = Producto.objects.filter(activo=True).order_by("nombre")

    activo_1 = None
    activo_2 = None

    activo_1_id = request.GET.get("activo_1")
    activo_2_id = request.GET.get("activo_2")

    if activo_1_id:
        activo_1 = Producto.objects.filter(id=activo_1_id, activo=True).first()

    if activo_2_id:
        activo_2 = Producto.objects.filter(id=activo_2_id, activo=True).first()

    metricas = [
        ("Precio actual", "precio_actual"),
        ("Score QuantEdge", "puntaje_quant"),
        ("Riesgo", "riesgo"),
        ("Recomendación", "recomendacion"),
        ("Variación diaria", "variacion_diaria"),
        ("Variación semanal", "variacion_semanal"),
        ("Variación mensual", "variacion_mensual"),
        ("P/E Ratio", "pe_ratio"),
        ("EPS", "eps"),
        ("Beta", "beta"),
        ("Dividendo", "dividendo"),
        ("Capitalización", "capitalizacion_mercado"),
        ("Volumen", "volumen"),
    ]

    contexto = {
        "activos": activos,
        "activo_1": activo_1,
        "activo_2": activo_2,
        "metricas": metricas,
    }

    return render(request, "vistaprevia/comparador.html", contexto)

def ranking_activos(request):
    activos = Producto.objects.filter(activo=True).order_by(
        "-puntaje_quant",
        "-confianza_modelo",
        "riesgo",
        "nombre"
    )

    return render(
        request,
        "vistaprevia/ranking.html",
        {"activos": activos}
    )