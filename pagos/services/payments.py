from datetime import datetime
from decimal import Decimal, InvalidOperation
import re
from django.db import transaction
from django.utils import timezone
from pagos.models import OrdenPago, PagoProveedor, EventoPago
from usuarios.models import InversionSimulada
from usuarios.services.inversiones import PortfolioService
from .mercado_pago import MercadoPagoClient, ProviderError

S = OrdenPago.Estado
FAILED_DETAILS = {
    "bad_filled_card_data", "invalid_card_token", "high_risk", "rejected_by_issuer",
    "required_call_for_authorize", "max_attempts_exceeded", "card_disabled",
    "card_insufficient_amount", "amount_limit_exceeded", "invalid_installments", "processing_error",
}


class VerificationError(Exception):
    pass


def money(value):
    try:
        number = Decimal(str(value))
        if not number.is_finite() or number < 0 or number > Decimal("9999999999.99") or number != number.quantize(Decimal("0.01")):
            raise ValueError
        return number
    except (ValueError, InvalidOperation):
        raise VerificationError("invalid_amount") from None


def code(value, maximum=64):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,%d}" % maximum, value):
        raise VerificationError("invalid_provider_field")
    return value


def provider_time(value):
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            raise ValueError
        return int(dt.timestamp() * 1000000)
    except (AttributeError, ValueError, TypeError, OverflowError):
        raise VerificationError("invalid_provider_timestamp") from None


def validate_remote(orden, data, expected_id):
    if not isinstance(data, dict) or data.get("id") != expected_id:
        raise VerificationError("order_id_mismatch")
    code(expected_id)
    if orden.mp_order_id and orden.mp_order_id != expected_id:
        raise VerificationError("order_association_mismatch")
    if data.get("external_reference") != str(orden.pk):
        raise VerificationError("external_reference_mismatch")
    if money(data.get("total_amount")) != orden.importe_demo or data.get("currency") != "ARS":
        raise VerificationError("amount_currency_mismatch")
    if (orden.environment != "test" or data.get("live_mode") is True
            or data.get("type") != "online" or data.get("processing_mode") != "manual"
            or data.get("country_code") not in {"AR", "ARG"}):
        raise VerificationError("context_mismatch")
    seller = code(str(data.get("user_id", "")))
    integration = data.get("integration_data")
    if not isinstance(integration, dict):
        raise VerificationError("application_missing")
    application = code(str(integration.get("application_id", "")))
    if not seller.isdigit() or not application.isdigit():
        raise VerificationError("seller_application_invalid")
    if ((orden.mp_user_id and seller != orden.mp_user_id)
            or (orden.mp_application_id and application != orden.mp_application_id)):
        raise VerificationError("seller_application_mismatch")
    return seller, application, provider_time(data.get("last_updated_date"))


def map_state(status, detail, transactions):
    if transactions.get("chargebacks"):
        return S.REVIEW_REQUIRED
    if detail == "partially_refunded":
        return S.REVIEW_REQUIRED
    mapping = {("created", "created"): S.PENDING,
               ("processing", "in_process"): S.PENDING,
               ("processing", "pending_review_manual"): S.PENDING,
               ("action_required", "waiting_capture"): S.ACTION_REQUIRED,
               ("processed", "accredited"): S.APPROVED,
               ("processed", "refunded"): S.REFUNDED,
               ("refunded", "refunded"): S.REFUNDED,
               ("canceled", "canceled"): S.CANCELLED}
    if status == "failed" and detail in FAILED_DETAILS:
        return S.REJECTED
    return mapping.get((status, detail), S.REVIEW_REQUIRED)


def audit(orden, source, result, previous):
    EventoPago.objects.create(orden=orden, origen=source, resultado=result,
                             estado_anterior=previous, estado_nuevo=orden.estado)


class PaymentService:
    @staticmethod
    def reconcile(orden, source="reconciliation", client=None):
        if not orden.mp_order_id:
            raise ProviderError("missing_remote_id")
        data = (client or MercadoPagoClient()).get_order(orden.mp_order_id)
        return PaymentService.apply(orden.pk, data, orden.mp_order_id, source)

    @staticmethod
    @transaction.atomic
    def apply(pk, data, expected_id, source="webhook"):
        orden = OrdenPago.objects.select_for_update().get(pk=pk)
        previous = orden.estado
        try:
            seller, application, updated = validate_remote(orden, data, expected_id)
            if orden.mp_updated_us is not None and updated < orden.mp_updated_us:
                audit(orden, source, "stale_ignored", previous)
                return orden
            status = code(data.get("status"))
            detail = code(data.get("status_detail"), 128)
            transactions = data.get("transactions", {})
            if not isinstance(transactions, dict):
                raise VerificationError("invalid_transactions")
            payments = transactions.get("payments", [])
            if not isinstance(payments, list):
                raise VerificationError("invalid_payments")
            normalized = []
            for payment in payments:
                if not isinstance(payment, dict):
                    raise VerificationError("invalid_payment")
                payment_id = code(payment.get("id"))
                if PagoProveedor.objects.filter(external_id=payment_id).exclude(orden=orden).exists():
                    raise VerificationError("payment_association_mismatch")
                if payment.get("currency", "ARS") != "ARS":
                    raise VerificationError("payment_currency_mismatch")
                normalized.append((payment_id, money(payment.get("amount")),
                                   code(payment.get("status")), code(payment.get("status_detail"), 128)))
            if len({p[0] for p in normalized}) != len(normalized):
                raise VerificationError("duplicate_payment_id")
            new = map_state(status, detail, transactions)
            if new == S.APPROVED:
                accredited = sum((p[1] for p in normalized if p[2:] == ("processed", "accredited")), Decimal("0"))
                if accredited != orden.importe_demo or money(data.get("total_paid_amount")) != orden.importe_demo:
                    raise VerificationError("accreditation_inconsistent")
        except VerificationError as exc:
            orden.estado = S.REVIEW_REQUIRED
            orden.ultimo_error = str(exc)
            orden.save(update_fields=["estado", "ultimo_error", "actualizada"])
            audit(orden, source, str(exc), previous)
            return orden

        if (orden.mp_updated_us == updated and orden.mp_status
                and (status, detail) != (orden.mp_status, orden.mp_status_detail)):
            new = S.REVIEW_REQUIRED
        # Financial effects are irreversible by an out-of-order approval/pending notification.
        if previous == S.REFUNDED:
            audit(orden, source, "terminal_ignored", previous)
            return orden
        if previous == S.APPROVED and new in {S.PENDING, S.ACTION_REQUIRED, S.REJECTED, S.CANCELLED}:
            audit(orden, source, "regression_ignored", previous)
            return orden
        if previous == S.REVIEW_REQUIRED and new != S.REFUNDED:
            new = S.REVIEW_REQUIRED
        for payment_id, amount, remote_status, remote_detail in normalized:
            payment, _ = PagoProveedor.objects.select_for_update().get_or_create(
                external_id=payment_id, defaults={"orden": orden, "importe": amount,
                    "moneda": "ARS", "estado": remote_status, "detalle": remote_detail})
            if payment.orden_id != orden.pk:
                # Another worker may have inserted the ID after initial validation.
                # Never reassign a provider transaction to a different internal order.
                raise ProviderError("payment_association_conflict")
            payment.estado, payment.detalle, payment.importe = remote_status, remote_detail, amount
            payment.save(update_fields=["estado", "detalle", "importe", "actualizado"])
        if new == S.APPROVED and orden.inversion_id is None:
            orden.inversion = PortfolioService.crear(usuario=orden.usuario, activo=orden.activo,
                cantidad=orden.cantidad, precio_compra=orden.precio_unitario)
            orden.aprobada = timezone.now()
        if new == S.REFUNDED:
            if orden.inversion_id:
                InversionSimulada.objects.filter(pk=orden.inversion_id).update(activa=False)
            orden.reembolsada = orden.reembolsada or timezone.now()
        orden.mp_order_id = expected_id
        orden.mp_user_id, orden.mp_application_id = seller, application
        orden.mp_status, orden.mp_status_detail = status, detail
        orden.mp_updated_us = updated
        orden.estado = new
        orden.ultimo_error = ""
        orden.save()
        audit(orden, source, "verified", previous)
        return orden
