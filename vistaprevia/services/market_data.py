from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

import requests
from django.conf import settings

from vistaprevia.exceptions import (
    MarketDataConfigurationError,
    MarketDataProviderError,
    MarketDataRequestError,
    MarketDataValidationError,
)


@dataclass(frozen=True)
class MarketQuote:
    symbol: str
    name: str
    currency: str
    exchange: str

    price: Decimal
    open_price: Decimal
    previous_close: Decimal
    high: Decimal
    low: Decimal

    change: Decimal
    percent_change: Decimal

    volume: int


class TwelveDataClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: int = 10,
    ):
        self.api_key = (
            api_key
            or getattr(settings, "TWELVE_DATA_API_KEY", "")
        )

        self.base_url = (
            base_url
            or getattr(
                settings,
                "TWELVE_DATA_BASE_URL",
                "https://api.twelvedata.com",
            )
        ).rstrip("/")

        self.timeout = timeout

        if not self.api_key:
            raise MarketDataConfigurationError(
                "TWELVE_DATA_API_KEY no está configurada."
            )

    @staticmethod
    def _decimal(
        value: Any,
        field_name: str,
        default: Decimal | None = None,
    ) -> Decimal:
        if value in (None, ""):
            if default is not None:
                return default

            raise MarketDataValidationError(
                f"El campo '{field_name}' no está presente."
            )

        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise MarketDataValidationError(
                f"El campo '{field_name}' contiene un valor inválido."
            ) from exc

    @staticmethod
    def _integer(
        value: Any,
        default: int = 0,
    ) -> int:
        if value in (None, ""):
            return default

        try:
            return int(Decimal(str(value)))
        except (InvalidOperation, TypeError, ValueError):
            return default

    def _get(
        self,
        endpoint: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        request_params = {
            **params,
            "apikey": self.api_key,
        }

        try:
            response = requests.get(
                f"{self.base_url}/{endpoint.lstrip('/')}",
                params=request_params,
                timeout=self.timeout,
            )

            response.raise_for_status()

        except requests.RequestException as exc:
            raise MarketDataRequestError(
                "No fue posible comunicarse con Twelve Data."
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise MarketDataValidationError(
                "Twelve Data devolvió una respuesta no válida."
            ) from exc

        if not isinstance(payload, dict):
            raise MarketDataValidationError(
                "Formato de respuesta inesperado."
            )

        if payload.get("status") == "error":
            raise MarketDataProviderError(
                payload.get(
                    "message",
                    "Twelve Data informó un error desconocido.",
                )
            )

        return payload

    def get_quote(
        self,
        symbol: str,
    ) -> MarketQuote:
        normalized_symbol = symbol.strip().upper()

        if not normalized_symbol:
            raise MarketDataValidationError(
                "Debe indicarse un símbolo."
            )

        payload = self._get(
            "quote",
            {
                "symbol": normalized_symbol,
            },
        )

        return MarketQuote(
            symbol=payload.get(
                "symbol",
                normalized_symbol,
            ),
            name=payload.get(
                "name",
                normalized_symbol,
            ),
            currency=payload.get(
                "currency",
                "USD",
            ),
            exchange=payload.get(
                "exchange",
                "",
            ),
            price=self._decimal(
                payload.get("close"),
                "close",
            ),
            open_price=self._decimal(
                payload.get("open"),
                "open",
            ),
            previous_close=self._decimal(
                payload.get("previous_close"),
                "previous_close",
            ),
            high=self._decimal(
                payload.get("high"),
                "high",
            ),
            low=self._decimal(
                payload.get("low"),
                "low",
            ),
            change=self._decimal(
                payload.get("change"),
                "change",
                Decimal("0"),
            ),
            percent_change=self._decimal(
                payload.get("percent_change"),
                "percent_change",
                Decimal("0"),
            ),
            volume=self._integer(
                payload.get("volume"),
            ),
        )