from django.conf import settings
from django.core.checks import Error, register
from django.core.exceptions import ImproperlyConfigured
from .conf import payment_config


@register()
def check_payments(app_configs, **kwargs):
    if not settings.MERCADOPAGO_ENABLED:
        return []
    try:
        payment_config()
    except ImproperlyConfigured as exc:
        return [Error(str(exc), id="pagos.E001")]
    return []
