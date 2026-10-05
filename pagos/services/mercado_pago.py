import re
import requests
from django.conf import settings
from pagos.conf import payment_config


class ProviderError(Exception):
    """Only fixed codes, never remote bodies, URLs with credentials or exceptions."""
    def __init__(self, code="provider_unavailable"):
        self.code = code
        super().__init__(code)


class MercadoPagoClient:
    BASE_URL = "https://api.mercadopago.com"

    def _request(self, method, path, **kwargs):
        payment_config()
        headers = {"Authorization": f"Bearer {settings.MERCADOPAGO_ACCESS_TOKEN}",
                   "Content-Type": "application/json", **kwargs.pop("headers", {})}
        try:
            response = requests.request(method, self.BASE_URL + path, headers=headers,
                                        timeout=(3, 7), allow_redirects=False, **kwargs)
            if response.status_code not in (200, 201):
                raise ProviderError("provider_http_error")
            data = response.json()
            if not isinstance(data, dict):
                raise ProviderError("provider_invalid_response")
            return data
        except (requests.RequestException, ValueError):
            raise ProviderError() from None

    def create_order(self, payload, idempotency_key):
        return self._request("POST", "/v1/orders", json=payload,
                             headers={"X-Idempotency-Key": str(idempotency_key)})

    def get_order(self, order_id):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", order_id):
            raise ProviderError("invalid_order_id")
        return self._request("GET", f"/v1/orders/{order_id}")
