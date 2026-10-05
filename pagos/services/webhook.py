import hashlib
import hmac
import json
import re
import uuid
from django.conf import settings
from pagos.conf import payment_config
from pagos.models import OrdenPago
from .mercado_pago import MercadoPagoClient, ProviderError
from .payments import PaymentService


class MalformedWebhook(Exception):
    pass


class InvalidSignature(Exception):
    pass


def verify_notification(request):
    payment_config()
    signature = request.headers.get("x-signature", "")
    request_id = request.headers.get("x-request-id", "").strip()
    if not signature or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", request_id):
        raise InvalidSignature
    ids = request.GET.getlist("data.id")
    if len(ids) != 1 or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", ids[0]):
        raise MalformedWebhook
    fields = {}
    for part in signature.split(","):
        pair = part.strip().split("=", 1)
        if len(pair) != 2 or pair[0] in fields:
            raise InvalidSignature
        fields[pair[0]] = pair[1]
    ts, digest = fields.get("ts", ""), fields.get("v1", "")
    if not re.fullmatch(r"[0-9]{1,20}", ts) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise InvalidSignature
    # Matches SDK 3.6.0: data.id exactly as received, no lowercasing.
    # No timestamp tolerance: upstream validator mixes seconds and milliseconds.
    manifest = f"id:{ids[0]};request-id:{request_id};ts:{ts};"
    expected = hmac.new(settings.MERCADOPAGO_WEBHOOK_SECRET.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, digest):
        raise InvalidSignature
    try:
        if len(request.body) > 32768:
            raise ValueError
        body = json.loads(request.body)
        if (not isinstance(body, dict) or body.get("type") != "order"
                or not isinstance(body.get("data"), dict) or body["data"].get("id") != ids[0]
                or request.GET.getlist("type") not in ([], ["order"])):
            raise ValueError
    except (ValueError, UnicodeDecodeError):
        raise MalformedWebhook from None
    return ids[0]


def process_notification(remote_id, client=None):
    data = (client or MercadoPagoClient()).get_order(remote_id)
    orden = OrdenPago.objects.filter(mp_order_id=remote_id).first()
    if orden is None:
        # Handles webhook arriving before the POST response has been persisted.
        try:
            reference = uuid.UUID(data.get("external_reference", ""))
        except (ValueError, TypeError, AttributeError):
            raise MalformedWebhook from None
        orden = OrdenPago.objects.filter(pk=reference, mp_order_id__isnull=True,
                                        ultimo_intento__isnull=False).first()
    if orden is None:
        raise MalformedWebhook
    return PaymentService.apply(orden.pk, data, remote_id, "webhook")
