from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import DatabaseError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from vistaprevia.models import Producto
from .conf import payment_config
from .forms import CheckoutForm
from .models import OrdenPago
from .services.checkout import create_internal, start_checkout, submission_token
from .services.mercado_pago import ProviderError
from .services.webhook import verify_notification, process_notification, InvalidSignature, MalformedWebhook


def owned_order(request, pk):
    return get_object_or_404(OrdenPago, pk=pk, usuario=request.user)


@login_required
@never_cache
@require_http_methods(["GET", "POST"])
def checkout(request, activo_id):
    activo = get_object_or_404(Producto, pk=activo_id, activo=True)
    try:
        amount, _ = payment_config()
    except ImproperlyConfigured:
        return render(request, "pagos/checkout.html", {"activo": activo, "disabled": True}, status=503)
    form = CheckoutForm(request.POST or None, initial={"token": submission_token(request.user, activo)})
    if request.method == "POST" and form.is_valid():
        try:
            orden = create_internal(user=request.user, activo=activo, **form.cleaned_data)
            return redirect(orden)
        except (ValidationError, Producto.DoesNotExist):
            form.add_error(None, "No se pudo crear la orden. Revisa los datos o abre un nuevo checkout.")
    return render(request, "pagos/checkout.html", {"activo": activo, "form": form, "importe_demo": amount})


@login_required
@never_cache
@require_GET
def orden_detalle(request, pk):
    return render(request, "pagos/orden_detalle.html", {"orden": owned_order(request, pk)})


@login_required
@never_cache
@require_POST
def iniciar(request, pk):
    orden = owned_order(request, pk)
    try:
        orden = start_checkout(orden.pk)
    except (ProviderError, ImproperlyConfigured):
        messages.error(request, "Checkout no disponible. La orden se conserva; espera 30 segundos antes de reintentar.")
        return redirect(orden)
    return redirect(orden.checkout_url)


@login_required
@never_cache
@require_GET
def estado(request, pk):
    orden = owned_order(request, pk)
    response = JsonResponse({"estado": orden.estado, "etiqueta": orden.get_estado_display(),
                             "continuar": orden.estado in {"PENDING", "ACTION_REQUIRED", "ERROR"}})
    response["X-Robots-Tag"] = "noindex, follow"
    return response


@login_required
@never_cache
@require_GET
def resultado(request, pk, outcome):
    return render(request, "pagos/resultado.html", {"orden": owned_order(request, pk), "outcome": outcome})


@login_required
@never_cache
@require_GET
def historial(request):
    from django.core.paginator import Paginator
    ordenes = Paginator(OrdenPago.objects.filter(usuario=request.user), 25).get_page(request.GET.get("page"))
    return render(request, "pagos/historial.html", {"ordenes": ordenes})


@csrf_exempt
@require_POST
def mercadopago_webhook(request):
    try:
        remote_id = verify_notification(request)
        process_notification(remote_id)
    except InvalidSignature:
        return HttpResponse(status=401)
    except MalformedWebhook:
        return HttpResponse(status=400)
    except (ProviderError, DatabaseError, ImproperlyConfigured):
        return HttpResponse(status=503)
    return HttpResponse(status=200)
