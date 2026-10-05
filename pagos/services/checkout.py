from datetime import timedelta
import uuid
from urllib.parse import urlsplit, parse_qs
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from vistaprevia.models import Producto
from pagos.conf import payment_config
from pagos.models import OrdenPago
from .mercado_pago import MercadoPagoClient, ProviderError
from .payments import VerificationError, validate_remote, audit


def submission_token(user, activo):
    return signing.dumps({"user": user.pk, "activo": activo.pk, "key": str(uuid.uuid4())}, salt="pagos.checkout")


def create_internal(*, user, activo, cantidad, token):
    amount, base = payment_config()
    try:
        intention = signing.loads(token, salt="pagos.checkout", max_age=86400)
        key = uuid.UUID(intention["key"])
        if intention["user"] != user.pk or intention["activo"] != activo.pk:
            raise ValueError
    except (signing.BadSignature, KeyError, ValueError, TypeError):
        raise ValidationError("Formulario vencido o invalido. Volve a abrir el checkout.") from None
    if not isinstance(cantidad, int) or not 1 <= cantidad <= 100000:
        raise ValidationError("Cantidad invalida.")
    with transaction.atomic():
        # Serializes simultaneous submissions for the same product and re-reads its price.
        activo = Producto.objects.select_for_update().get(pk=activo.pk, activo=True)
        existing = OrdenPago.objects.filter(submission_key=key).first()
        if existing:
            if existing.usuario_id != user.pk or existing.activo_id != activo.pk or existing.cantidad != cantidad:
                raise ValidationError("La intencion ya existe con otros datos.")
            return existing
        if activo.precio_actual <= 0:
            raise ValidationError("El activo no tiene una cotizacion valida.")
        orden = OrdenPago(usuario=user, activo=activo, cantidad=cantidad, submission_key=key,
                          nombre_snapshot=activo.nombre, simbolo_snapshot=activo.simbolo,
                          precio_unitario=activo.precio_actual, moneda_activo=activo.moneda,
                          importe_demo=amount)
        orden.checkout_payload = {
            "type": "online", "processing_mode": "manual", "capture_mode": "automatic",
            "external_reference": str(orden.pk), "total_amount": format(amount, ".2f"),
            "items": [{"title": "QuantEdge - demostracion de pago (sin compra de activos)",
                       "quantity": 1, "unit_price": format(amount, ".2f")}],
            "config": {"online": {**{f"{name}_url": base + reverse(f"pagos:{name}", kwargs={"pk": orden.pk})
                                      for name in ("success", "pending", "failure")}, "auto_return": "approved"}},
        }
        orden.save()
        return orden


def start_checkout(pk, client=None):
    payment_config()
    with transaction.atomic():
        orden = OrdenPago.objects.select_for_update().get(pk=pk)
        if not orden.puede_iniciar:
            raise ProviderError("order_not_payable")
        if orden.mp_order_id and orden.checkout_url:
            return orden
        if orden.ultimo_intento and orden.ultimo_intento > timezone.now() - timedelta(seconds=30):
            raise ProviderError("creation_in_progress")
        orden.ultimo_intento = timezone.now()
        orden.estado = OrdenPago.Estado.PENDING
        orden.save(update_fields=["ultimo_intento", "estado", "actualizada"])
    try:
        data = (client or MercadoPagoClient()).create_order(orden.checkout_payload, orden.idempotency_key)
        remote_id = data.get("id")
        validate_remote(orden, data, remote_id)
        url = data.get("checkout_url", "")
        try:
            parsed = urlsplit(url) if isinstance(url, str) else None
        except ValueError:
            parsed = None
        if (parsed is None or len(url) > 1000 or parsed.scheme != "https" or parsed.netloc != "www.mercadopago.com.ar"
                or parsed.path != "/checkout/v1/redirect" or parsed.fragment
                or parse_qs(parsed.query).get("order_id") != [remote_id]):
            raise VerificationError("invalid_checkout_url")
        with transaction.atomic():
            locked = OrdenPago.objects.select_for_update().get(pk=pk)
            validate_remote(locked, data, remote_id)
            locked.mp_order_id = remote_id
            locked.checkout_url = url
            locked.mp_user_id = str(data["user_id"])
            locked.mp_application_id = str(data["integration_data"]["application_id"])
            locked.save(update_fields=["mp_order_id", "checkout_url", "mp_user_id", "mp_application_id", "actualizada"])
        # Creation never credits the portfolio. Only a subsequent GET can do that.
        return OrdenPago.objects.get(pk=pk)
    except (ProviderError, VerificationError) as exc:
        with transaction.atomic():
            locked = OrdenPago.objects.select_for_update().get(pk=pk)
            previous = locked.estado
            if previous in {OrdenPago.Estado.CREATED, OrdenPago.Estado.PENDING, OrdenPago.Estado.ERROR}:
                locked.estado = OrdenPago.Estado.REVIEW_REQUIRED if isinstance(exc, VerificationError) else OrdenPago.Estado.ERROR
                locked.ultimo_error = str(exc)
                locked.save(update_fields=["estado", "ultimo_error", "actualizada"])
                audit(locked, "checkout", str(exc), previous)
        raise ProviderError("checkout_unavailable") from None
