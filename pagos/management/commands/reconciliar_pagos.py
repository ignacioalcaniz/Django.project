from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ImproperlyConfigured
from django.db import DatabaseError
from pagos.conf import payment_config
from pagos.models import OrdenPago
from pagos.services.checkout import start_checkout
from pagos.services.mercado_pago import ProviderError
from pagos.services.payments import PaymentService


class Command(BaseCommand):
    help = "Concilia ordenes demo recuperables; nunca inicia nuevas intenciones."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        try:
            payment_config()
        except ImproperlyConfigured as exc:
            raise CommandError(str(exc)) from None
        if not 1 <= options["limit"] <= 1000:
            raise CommandError("limit debe estar entre 1 y 1000")
        orders = OrdenPago.objects.filter(estado__in=["PENDING", "ACTION_REQUIRED", "ERROR"]).order_by("actualizada")[:options["limit"]]
        ok = errors = 0
        for orden in orders:
            try:
                if not orden.mp_order_id:
                    orden = start_checkout(orden.pk)
                PaymentService.reconcile(orden)
                ok += 1
            except (ProviderError, DatabaseError):
                errors += 1
        self.stdout.write(f"Conciliadas: {ok}; errores recuperables: {errors}")
        if errors:
            raise CommandError("Hay ordenes pendientes de reintento; revisar auditoria.")
