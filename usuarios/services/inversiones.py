from usuarios.models import InversionSimulada


class PortfolioService:
    @staticmethod
    def crear(*, usuario, activo, cantidad, precio_compra):
        """Caller owns the transaction when this is part of a payment approval."""
        return InversionSimulada.objects.create(
            usuario=usuario, activo=activo, cantidad=cantidad,
            precio_compra=precio_compra, activa=True,
        )
