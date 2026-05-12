from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from .forms import RegistroUsuarioForm
from .models import InversionSimulada, ConsultaIA
from vistaprevia.models import Producto


def registro(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = RegistroUsuarioForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Cuenta creada correctamente. Bienvenido a QuantEdge.")
            return redirect("dashboard")
    else:
        form = RegistroUsuarioForm()

    return render(request, "usuarios/registro.html", {"form": form})


def cerrar_sesion(request):
    logout(request)
    return redirect("home")


def generar_respuesta_ia(activo):
    if activo.recomendacion == "comprar":
        decision = "La señal actual es favorable, aunque conviene revisar tu perfil de riesgo antes de invertir."
    elif activo.recomendacion == "vender":
        decision = "La señal actual indica cautela. Podría ser mejor reducir exposición o esperar una confirmación."
    elif activo.recomendacion == "observar":
        decision = "La IA sugiere observar el activo antes de tomar una decisión porque presenta señales mixtas."
    else:
        decision = "La IA sugiere mantener la posición y seguir monitoreando próximos movimientos."

    return (
        f"Análisis QuantEdge IA para {activo.nombre} ({activo.simbolo}): "
        f"precio actual {activo.moneda} {activo.precio_actual}, "
        f"variación diaria {activo.variacion_diaria}%, "
        f"riesgo {activo.get_riesgo_display()}, "
        f"score QuantEdge {activo.puntaje_quant}/100. "
        f"{decision} Este asesoramiento es informativo y no constituye recomendación financiera profesional."
    )


@login_required
def dashboard(request):
    activos = Producto.objects.filter(activo=True).order_by("-es_destacado", "-puntaje_quant", "nombre")
    inversiones = InversionSimulada.objects.filter(usuario=request.user).select_related("activo")
    consultas = ConsultaIA.objects.filter(usuario=request.user).select_related("activo")[:5]

    total_invertido = sum(inversion.total_invertido() for inversion in inversiones)

    contexto = {
        "usuario": request.user,
        "activos": activos,
        "inversiones": inversiones,
        "consultas": consultas,
        "total_invertido": total_invertido,
        "cantidad_inversiones": inversiones.count(),
        "cantidad_consultas": consultas.count(),
    }

    return render(request, "usuarios/dashboard.html", contexto)


@login_required
def comprar_activo(request, activo_id):
    if request.method != "POST":
        return redirect("dashboard")

    activo = get_object_or_404(Producto, id=activo_id, activo=True)
    cantidad = request.POST.get("cantidad", 1)

    try:
        cantidad = int(cantidad)
    except ValueError:
        cantidad = 1

    if cantidad < 1:
        cantidad = 1

    InversionSimulada.objects.create(
        usuario=request.user,
        activo=activo,
        cantidad=cantidad,
        precio_compra=activo.precio_actual
    )

    messages.success(request, f"Compra simulada realizada: {cantidad} acción/es de {activo.simbolo}.")
    return redirect("dashboard")


@login_required
def asesorar_activo(request, activo_id):
    if request.method != "POST":
        return redirect("dashboard")

    activo = get_object_or_404(Producto, id=activo_id, activo=True)
    pregunta = request.POST.get("pregunta", "")

    respuesta = generar_respuesta_ia(activo)

    ConsultaIA.objects.create(
        usuario=request.user,
        activo=activo,
        pregunta=pregunta,
        respuesta=respuesta
    )

    messages.success(request, f"Asesoramiento IA generado para {activo.simbolo}.")
    return redirect("dashboard")
