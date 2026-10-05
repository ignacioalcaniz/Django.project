from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def payment_config():
    """Fail closed; never include values of credentials in errors."""
    if not settings.MERCADOPAGO_ENABLED:
        raise ImproperlyConfigured("Checkout de prueba deshabilitado.")
    if settings.MERCADOPAGO_ENVIRONMENT != "test":
        raise ImproperlyConfigured("Esta entrega admite exclusivamente environment=test.")
    if not settings.MERCADOPAGO_ACCESS_TOKEN.startswith("TEST-"):
        raise ImproperlyConfigured("Se requiere Access Token de prueba TEST-. Ver pagos/README.md.")
    if not settings.MERCADOPAGO_WEBHOOK_SECRET:
        raise ImproperlyConfigured("Falta MERCADOPAGO_WEBHOOK_SECRET.")
    try:
        amount = Decimal(settings.MERCADOPAGO_DEMO_AMOUNT_ARS)
        valid = amount.is_finite() and 0 < amount <= Decimal("9999999999.99") and amount == amount.quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        valid = False
    if not valid:
        raise ImproperlyConfigured("MERCADOPAGO_DEMO_AMOUNT_ARS debe ser positivo, con hasta dos decimales.")
    base = settings.MERCADOPAGO_PUBLIC_BASE_URL.rstrip("/")
    try:
        parsed = urlsplit(base)
        parsed.port  # Validate malformed ports before they reach return URLs.
    except ValueError:
        raise ImproperlyConfigured("MERCADOPAGO_PUBLIC_BASE_URL invalida.") from None
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.query or parsed.fragment or parsed.path
            or parsed.hostname in {"localhost", "127.0.0.1", "::1"}):
        raise ImproperlyConfigured("MERCADOPAGO_PUBLIC_BASE_URL requiere un origen HTTPS publico sin path.")
    return amount, base
