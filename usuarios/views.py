from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET

from vistaprevia.models import Producto

from .forms import PerfilUsuarioForm, RegistroUsuarioForm
from .models import (
    ActivoFavorito,
    ConsultaIA,
    InversionSimulada,
    Notificacion,
    PerfilUsuario,
)


def registro(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = RegistroUsuarioForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)

            messages.success(
                request,
                "Cuenta creada correctamente. Bienvenido a QuantEdge.",
            )

            return redirect("dashboard")
    else:
        form = RegistroUsuarioForm()

    return render(
        request,
        "usuarios/registro.html",
        {"form": form},
    )


def cerrar_sesion(request):
    logout(request)
    return redirect("home")


def obtener_estado_mercado(activo):
    if activo.puntaje_quant >= 85:
        return (
            "El activo presenta un score QuantEdge excelente "
            "dentro del universo analizado."
        )

    if activo.puntaje_quant >= 70:
        return (
            "El activo presenta una lectura favorable, "
            "aunque todavía requiere seguimiento."
        )

    if activo.puntaje_quant >= 50:
        return (
            "El activo muestra señales mixtas y conviene "
            "analizarlo con prudencia."
        )

    return (
        "El activo presenta una lectura débil y requiere "
        "cautela antes de tomar decisiones."
    )


def obtener_lectura_recomendacion(activo):
    if activo.recomendacion == "comprar":
        return (
            "La recomendación actual es positiva. "
            "El modelo interpreta que existen condiciones "
            "favorables para evaluar una entrada."
        )

    if activo.recomendacion == "vender":
        return (
            "La recomendación actual indica reducción de exposición "
            "o salida. El modelo detecta señales de riesgo o debilidad."
        )

    if activo.recomendacion == "observar":
        return (
            "La recomendación actual es observar. "
            "El activo puede tener potencial, pero todavía no muestra "
            "suficiente confirmación."
        )

    return (
        "La recomendación actual es mantener. "
        "El activo no presenta una señal clara de compra "
        "o venta inmediata."
    )


def obtener_lectura_perfil(activo, perfil_inversor):
    if perfil_inversor == "conservador":
        return (
            "Para un perfil conservador, la prioridad debería ser "
            "preservar capital, limitar exposición y evitar entradas "
            "impulsivas. Si el riesgo del activo es alto o la beta es "
            "elevada, conviene esperar mayor confirmación antes de operar."
        )

    if perfil_inversor == "agresivo":
        return (
            "Para un perfil agresivo, el activo puede ser evaluado con "
            "mayor tolerancia a la volatilidad. Aun así, conviene gestionar "
            "tamaño de posición, puntos de salida y exposición total "
            "del portfolio."
        )

    return (
        "Para un perfil moderado, una estrategia razonable sería analizar "
        "una entrada gradual, combinando potencial de crecimiento "
        "con control de riesgo."
    )


def generar_puntos_positivos(activo):
    puntos = []

    if activo.puntaje_quant >= 70:
        puntos.append(
            f"Score QuantEdge sólido de {activo.puntaje_quant}/100."
        )

    if activo.variacion_diaria > 0:
        puntos.append(
            f"Variación diaria positiva de {activo.variacion_diaria}%."
        )

    if activo.variacion_semanal > 0:
        puntos.append(
            f"Variación semanal positiva de {activo.variacion_semanal}%."
        )

    if activo.variacion_mensual > 0:
        puntos.append(
            f"Variación mensual positiva de {activo.variacion_mensual}%."
        )

    if activo.recomendacion == "comprar":
        puntos.append(
            "La recomendación interna del modelo es comprar."
        )

    if activo.confianza_modelo >= 70:
        puntos.append(
            f"Confianza del modelo elevada: "
            f"{activo.confianza_modelo}%."
        )

    if not puntos:
        puntos.append(
            "No se detectan señales positivas fuertes "
            "con los datos actuales."
        )

    return puntos


def generar_riesgos(activo):
    riesgos = []

    if activo.riesgo == "alto":
        riesgos.append(
            "El activo está clasificado como de riesgo alto."
        )

    if activo.beta and activo.beta > 1:
        riesgos.append(
            f"Beta superior a 1 ({activo.beta}), lo que indica "
            "mayor sensibilidad al mercado."
        )

    if activo.variacion_diaria < 0:
        riesgos.append(
            f"Variación diaria negativa de {activo.variacion_diaria}%."
        )

    if activo.variacion_semanal < 0:
        riesgos.append(
            f"Variación semanal negativa de {activo.variacion_semanal}%."
        )

    if activo.variacion_mensual < 0:
        riesgos.append(
            f"Variación mensual negativa de {activo.variacion_mensual}%."
        )

    if activo.pe_ratio and activo.pe_ratio > 40:
        riesgos.append(
            f"P/E Ratio elevado ({activo.pe_ratio}), "
            "posible señal de valuación exigente."
        )

    if activo.recomendacion in ["vender", "observar"]:
        riesgos.append(
            f"La recomendación actual es "
            f"{activo.get_recomendacion_display()}, "
            "por lo que conviene actuar con prudencia."
        )

    if not riesgos:
        riesgos.append(
            "No se detectan riesgos críticos con los datos actuales, "
            "aunque toda inversión implica incertidumbre."
        )

    return riesgos


def generar_respuesta_ia(
    activo,
    perfil_inversor="moderado",
    pregunta="",
):
    estado_mercado = obtener_estado_mercado(activo)
    lectura_recomendacion = obtener_lectura_recomendacion(activo)
    lectura_perfil = obtener_lectura_perfil(
        activo,
        perfil_inversor,
    )
    puntos_positivos = generar_puntos_positivos(activo)
    riesgos = generar_riesgos(activo)

    puntos_texto = "\n".join(
        f"- {punto}" for punto in puntos_positivos
    )

    riesgos_texto = "\n".join(
        f"- {riesgo}" for riesgo in riesgos
    )

    pregunta_texto = (
        pregunta.strip()
        if pregunta
        else "Consulta general del activo."
    )

    return (
        "ANÁLISIS QUANTEDGE IA\n\n"
        f"Activo analizado: {activo.nombre} ({activo.simbolo})\n"
        f"Sector: {activo.sector or 'Sin sector cargado'}\n"
        f"Bolsa: {activo.bolsa or 'Sin bolsa cargada'}\n"
        f"Pregunta del usuario: {pregunta_texto}\n\n"
        "1. RESUMEN DEL ACTIVO\n"
        f"El activo cotiza actualmente a "
        f"{activo.moneda} {activo.precio_actual}. "
        f"Su variación diaria es de {activo.variacion_diaria}%, "
        f"la semanal de {activo.variacion_semanal}% "
        f"y la mensual de {activo.variacion_mensual}%. "
        f"El score QuantEdge es {activo.puntaje_quant}/100 "
        f"y el riesgo asignado es "
        f"{activo.get_riesgo_display()}. "
        f"{estado_mercado}\n\n"
        "2. PUNTOS POSITIVOS\n"
        f"{puntos_texto}\n\n"
        "3. RIESGOS A CONSIDERAR\n"
        f"{riesgos_texto}\n\n"
        "4. LECTURA SEGÚN PERFIL INVERSOR\n"
        f"{lectura_perfil}\n\n"
        "5. RECOMENDACIÓN INTERNA\n"
        f"{lectura_recomendacion} "
        f"La confianza del modelo es de "
        f"{activo.confianza_modelo}%.\n\n"
        "6. CONCLUSIÓN\n"
        f"Con los datos disponibles, {activo.nombre} debe analizarse "
        "combinando score, riesgo, tendencia reciente y perfil del "
        "inversor. La decisión no debería basarse en un único indicador, "
        "sino en una evaluación integral del portfolio, horizonte temporal "
        "y tolerancia al riesgo.\n\n"
        "AVISO LEGAL\n"
        "Este análisis es informativo y educativo. "
        "No constituye asesoramiento financiero profesional "
        "ni una orden de compra o venta."
    )


def calcular_metricas_portfolio(inversiones):
    total_invertido = sum(
        inversion.total_invertido()
        for inversion in inversiones
    )

    valor_actual_total = sum(
        inversion.valor_actual()
        for inversion in inversiones
    )

    ganancia_total = valor_actual_total - total_invertido

    if total_invertido > 0:
        rentabilidad_total = (
            ganancia_total / total_invertido
        ) * Decimal("100")
    else:
        rentabilidad_total = Decimal("0.00")

    cantidad_inversiones = len(inversiones)

    if cantidad_inversiones > 0:
        score_promedio = sum(
            inversion.activo.puntaje_quant
            for inversion in inversiones
        ) / cantidad_inversiones
    else:
        score_promedio = 0

    mapa_riesgo = {
        "bajo": 1,
        "medio": 2,
        "alto": 3,
    }

    if cantidad_inversiones > 0:
        riesgo_num = sum(
            mapa_riesgo.get(
                inversion.activo.riesgo,
                2,
            )
            for inversion in inversiones
        ) / cantidad_inversiones
    else:
        riesgo_num = 0

    if riesgo_num >= 2.6:
        riesgo_promedio = "Alto"
    elif riesgo_num >= 1.6:
        riesgo_promedio = "Medio"
    elif riesgo_num > 0:
        riesgo_promedio = "Bajo"
    else:
        riesgo_promedio = "Sin datos"

    activo_mas_rentable = None

    if inversiones:
        activo_mas_rentable = max(
            inversiones,
            key=lambda inversion: (
                inversion.rentabilidad_porcentual()
            ),
        )

    return {
        "total_invertido": total_invertido,
        "valor_actual_total": valor_actual_total,
        "ganancia_total": ganancia_total,
        "rentabilidad_total": rentabilidad_total,
        "score_promedio": score_promedio,
        "riesgo_promedio": riesgo_promedio,
        "activo_mas_rentable": activo_mas_rentable,
    }


def generar_datos_graficos_portfolio(inversiones):
    labels = []
    valores_actuales = []
    rentabilidades = []
    scores = []

    for inversion in inversiones:
        labels.append(inversion.activo.simbolo)
        valores_actuales.append(
            float(inversion.valor_actual())
        )
        rentabilidades.append(
            float(inversion.rentabilidad_porcentual())
        )
        scores.append(
            float(inversion.activo.puntaje_quant)
        )

    return {
        "portfolio_labels": labels,
        "portfolio_valores": valores_actuales,
        "portfolio_rentabilidades": rentabilidades,
        "portfolio_scores": scores,
    }


def obtener_activos_filtrados(
    search="",
    recommendation="",
    risk="",
):
    activos = Producto.objects.filter(activo=True)

    if search:
        activos = activos.filter(
            Q(nombre__icontains=search)
            | Q(simbolo__icontains=search)
            | Q(sector__icontains=search)
            | Q(bolsa__icontains=search)
        )

    recomendaciones_validas = {
        "comprar",
        "mantener",
        "observar",
        "vender",
    }

    riesgos_validos = {
        "bajo",
        "medio",
        "alto",
    }

    if recommendation in recomendaciones_validas:
        activos = activos.filter(
            recomendacion=recommendation
        )

    if risk in riesgos_validos:
        activos = activos.filter(
            riesgo=risk
        )

    return activos.order_by(
        "-es_destacado",
        "-puntaje_quant",
        "nombre",
    )


@login_required
def dashboard(request):
    perfil, _ = PerfilUsuario.objects.get_or_create(
        usuario=request.user
    )

    activos = obtener_activos_filtrados()

    inversiones = list(
        InversionSimulada.objects
        .filter(usuario=request.user)
        .select_related("activo")
        .order_by("-fecha_compra")
    )

    consultas_queryset = (
        ConsultaIA.objects
        .filter(usuario=request.user)
        .select_related("activo")
        .order_by("-fecha_creacion")
    )

    consultas = consultas_queryset[:5]

    favoritos = (
        ActivoFavorito.objects
    .filter(usuario=request.user)
    .select_related("activo")
    .order_by("-fecha_agregado")
    )

    metricas_portfolio = calcular_metricas_portfolio(
        inversiones
    )

    datos_graficos = generar_datos_graficos_portfolio(
        inversiones
    )

    contexto = {
        "usuario": request.user,
        "perfil": perfil,
        "activos": activos,
        "inversiones": inversiones,
        "consultas": consultas,
        "favoritos": favoritos,
        "total_invertido": (
            metricas_portfolio["total_invertido"]
        ),
        "valor_actual_total": (
            metricas_portfolio["valor_actual_total"]
        ),
        "ganancia_total": (
            metricas_portfolio["ganancia_total"]
        ),
        "rentabilidad_total": (
            metricas_portfolio["rentabilidad_total"]
        ),
        "score_promedio": (
            metricas_portfolio["score_promedio"]
        ),
        "riesgo_promedio": (
            metricas_portfolio["riesgo_promedio"]
        ),
        "activo_mas_rentable": (
            metricas_portfolio["activo_mas_rentable"]
        ),
        "portfolio_labels": (
            datos_graficos["portfolio_labels"]
        ),
        "portfolio_valores": (
            datos_graficos["portfolio_valores"]
        ),
        "portfolio_rentabilidades": (
            datos_graficos["portfolio_rentabilidades"]
        ),
        "portfolio_scores": (
            datos_graficos["portfolio_scores"]
        ),
        "cantidad_inversiones": len(inversiones),
        "cantidad_consultas": consultas_queryset.count(),
        "cantidad_favoritos": favoritos.count(),
    }

    return render(
        request,
        "usuarios/dashboard.html",
        contexto,
    )


@login_required
@require_GET
def buscar_activos_ajax(request):
    search = request.GET.get("search", "").strip()

    recommendation = request.GET.get(
        "recommendation",
        "",
    ).strip().lower()

    risk = request.GET.get(
        "risk",
        "",
    ).strip().lower()

    search = search[:100]

    activos = obtener_activos_filtrados(
        search=search,
        recommendation=recommendation,
        risk=risk,
    )

    cantidad_resultados = activos.count()

    html = render_to_string(
        "usuarios/partials/_asset_cards.html",
        {
            "activos": activos,
        },
        request=request,
    )

    response = JsonResponse(
        {
            "success": True,
            "html": html,
            "count": cantidad_resultados,
            "filters": {
                "search": search,
                "recommendation": recommendation,
                "risk": risk,
            },
        }
    )

    response["Cache-Control"] = (
        "no-store, no-cache, must-revalidate, max-age=0"
    )

    return response


@login_required
def perfil_usuario(request):
    perfil, _ = PerfilUsuario.objects.get_or_create(
        usuario=request.user
    )

    if request.method == "POST":
        form = PerfilUsuarioForm(
            request.POST,
            request.FILES,
            instance=perfil,
        )

        if form.is_valid():
            perfil_actualizado = form.save(
                commit=False
            )

            if request.POST.get("eliminar_foto") == "on":
                if perfil_actualizado.foto:
                    perfil_actualizado.foto.delete(
                        save=False
                    )

                perfil_actualizado.foto = None

            perfil_actualizado.save()

            messages.success(
                request,
                "Perfil actualizado correctamente.",
            )

            return redirect("perfil_usuario")
    else:
        form = PerfilUsuarioForm(
            instance=perfil
        )

    inversiones = (
        InversionSimulada.objects
        .filter(usuario=request.user)
        .select_related("activo")
        .order_by("-fecha_compra")
    )

    consultas = (
        ConsultaIA.objects
        .filter(usuario=request.user)
        .select_related("activo")
        .order_by("-fecha_creacion")[:5]
    )

    contexto = {
        "perfil": perfil,
        "form": form,
        "inversiones": inversiones,
        "consultas": consultas,
    }

    return render(
        request,
        "usuarios/perfil.html",
        contexto,
    )


@login_required
def comprar_activo(request, activo_id):
    if request.method != "POST":
        return redirect("dashboard")

    activo = get_object_or_404(
        Producto,
        id=activo_id,
        activo=True,
    )

    try:
        cantidad = int(
            request.POST.get("cantidad", 1)
        )
    except (TypeError, ValueError):
        cantidad = 1

    cantidad = max(1, min(cantidad, 100000))

    InversionSimulada.objects.create(
        usuario=request.user,
        activo=activo,
        cantidad=cantidad,
        precio_compra=activo.precio_actual,
    )

    messages.success(
        request,
        (
            f"Compra simulada realizada: "
            f"{cantidad} acción/es de {activo.simbolo}."
        ),
    )

    return redirect("dashboard")


@login_required
def asesorar_activo(request, activo_id):
    if request.method != "POST":
        return redirect("dashboard")

    activo = get_object_or_404(
        Producto,
        id=activo_id,
        activo=True,
    )

    perfil, _ = PerfilUsuario.objects.get_or_create(
        usuario=request.user
    )

    pregunta = request.POST.get(
        "pregunta",
        "",
    ).strip()

    pregunta = pregunta[:500]

    respuesta = generar_respuesta_ia(
        activo=activo,
        perfil_inversor=perfil.perfil_inversor,
        pregunta=pregunta,
    )

    consulta = ConsultaIA.objects.create(
        usuario=request.user,
        activo=activo,
        pregunta=pregunta,
        respuesta=respuesta,
    )

    messages.success(
        request,
        (
            f"Análisis IA generado para "
            f"{activo.simbolo}."
        ),
    )

    return redirect(
        "detalle_analisis",
        consulta_id=consulta.id,
    )


@login_required
def alternar_favorito(request, activo_id):
    if request.method != "POST":
        return redirect("dashboard")

    activo = get_object_or_404(
        Producto,
        id=activo_id,
        activo=True,
    )

    favorito, creado = (
        ActivoFavorito.objects.get_or_create(
            usuario=request.user,
            activo=activo,
        )
    )

    if creado:
        messages.success(
            request,
            (
                f"{activo.simbolo} agregado "
                "a tu watchlist."
            ),
        )
    else:
        favorito.delete()

        messages.success(
            request,
            (
                f"{activo.simbolo} eliminado "
                "de tu watchlist."
            ),
        )

    next_url = request.POST.get(
        "next",
        "dashboard",
    )

    return redirect(next_url)


@login_required
def detalle_analisis(request, consulta_id):
    consulta = get_object_or_404(
        ConsultaIA.objects.select_related(
            "activo"
        ),
        id=consulta_id,
        usuario=request.user,
    )

    return render(
        request,
        "usuarios/analisis_ia.html",
        {"consulta": consulta},
    )


@login_required
def historial_ia(request):
    consultas = (
        ConsultaIA.objects
        .filter(usuario=request.user)
        .select_related("activo")
        .order_by("-fecha_creacion")
    )

    return render(
        request,
        "usuarios/historial_ia.html",
        {"consultas": consultas},
    )


@login_required
def notificaciones(request):
    notificaciones_usuario = (
        Notificacion.objects
        .filter(usuario=request.user)
        .order_by("-fecha_creacion")
    )

    return render(
        request,
        "usuarios/notificaciones.html",
        {
            "notificaciones": notificaciones_usuario,
        },
    )


@login_required
def marcar_notificaciones_leidas(request):
    if request.method == "POST":
        Notificacion.objects.filter(
            usuario=request.user,
            leida=False,
        ).update(leida=True)

    return redirect("notificaciones")