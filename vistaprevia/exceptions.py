class MarketDataError(Exception):
    """Error base de integración con el proveedor de datos de mercado."""


class MarketDataConfigurationError(MarketDataError):
    """Configuración inválida o incompleta del proveedor."""


class MarketDataRequestError(MarketDataError):
    """Error de red o comunicación con el proveedor."""


class MarketDataProviderError(MarketDataError):
    """El proveedor respondió correctamente, pero informó un error."""


class MarketDataValidationError(MarketDataError):
    """La respuesta externa no contiene datos válidos o esperados."""