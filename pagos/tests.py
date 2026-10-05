from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
import hashlib
import hmac
import io
import json
import threading
from unittest.mock import Mock, patch
import uuid
import requests
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.management import call_command
from django.db import close_old_connections, connection
from django.test import TestCase, TransactionTestCase, Client, override_settings, skipUnlessDBFeature
from django.urls import reverse
from django.utils import timezone
from pagos.conf import payment_config
from pagos.models import OrdenPago, PagoProveedor, EventoPago
from pagos.services.checkout import create_internal, start_checkout, submission_token
from pagos.services.mercado_pago import MercadoPagoClient, ProviderError
from pagos.services.payments import PaymentService
from usuarios.models import InversionSimulada, Notificacion
from vistaprevia.models import Producto

CONFIG = dict(MERCADOPAGO_ENABLED=True, MERCADOPAGO_ENVIRONMENT="test",
              MERCADOPAGO_ACCESS_TOKEN="TEST-fake-offline", MERCADOPAGO_WEBHOOK_SECRET="fake-webhook-secret",
              MERCADOPAGO_PUBLIC_BASE_URL="https://demo.example", MERCADOPAGO_DEMO_AMOUNT_ARS="1000.00",
              ALLOWED_HOSTS=["testserver"])


def remote(order, status="processed", detail="accredited", date="2026-09-30T12:00:00Z"):
    return {"id": order.mp_order_id or "ORDTST123", "type": "online", "processing_mode": "manual",
            "external_reference": str(order.pk), "total_amount": "1000.00", "total_paid_amount": "1000.00",
            "currency": "ARS", "country_code": "ARG", "user_id": "123", "integration_data": {"application_id": "456"},
            "status": status, "status_detail": detail, "last_updated_date": date,
            "checkout_url": "https://www.mercadopago.com.ar/checkout/v1/redirect?order_id=" + (order.mp_order_id or "ORDTST123"),
            "transactions": {"payments": [{"id": "PAY123", "amount": "1000.00", "status": status, "status_detail": detail}]}}


class OfflineMixin:
    def setUp(self):
        super().setUp()
        blocker = patch("requests.sessions.Session.request", side_effect=AssertionError("HTTP REAL PROHIBIDO"))
        self.http_guard = blocker.start()
        self.addCleanup(blocker.stop)

    def order(self):
        order = create_internal(user=self.user, activo=self.activo, cantidad=2,
                                token=submission_token(self.user, self.activo))
        order.mp_order_id = "ORDTST" + order.pk.hex
        order.estado = "PENDING"
        order.save()
        return order


@override_settings(**CONFIG)
class PaymentTests(OfflineMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="buyer")
        cls.other = get_user_model().objects.create_user(username="other")
        cls.activo = Producto.objects.create(nombre="Apple", simbolo="AAPL", precio_actual=Decimal("250.00"), moneda="USD")

    def url(self, name, order=None):
        return reverse("pagos:" + name, kwargs={"pk": order.pk}) if order else reverse("pagos:checkout", kwargs={"activo_id": self.activo.pk})

    def login(self):
        self.client.force_login(self.user)

    def test_anonymous_checkout_denied(self):
        self.assertEqual(self.client.get(self.url("checkout")).status_code, 302)
        self.assertEqual(self.client.post(self.url("checkout"), {}).status_code, 302)
        self.assertFalse(OrdenPago.objects.exists())

    def test_authenticated_internal_order_and_server_price(self):
        self.login()
        response = self.client.get(self.url("checkout"))
        token = response.context["form"].initial["token"]
        response = self.client.post(self.url("checkout"), {"cantidad": 2, "token": token, "precio": "0.01", "importe_demo": "0.01"})
        self.assertEqual(response.status_code, 302)
        order = OrdenPago.objects.get()
        self.assertEqual(order.precio_unitario, Decimal("250"))
        self.assertEqual(order.total_financiero, Decimal("500"))
        self.assertEqual(order.importe_demo, Decimal("1000"))
        self.assertEqual(order.moneda_activo, "USD")
        self.assertEqual(order.checkout_payload["items"][0]["quantity"], 1)
        self.assertFalse(InversionSimulada.objects.exists())

    def test_double_submit_same_order(self):
        token = submission_token(self.user, self.activo)
        first = create_internal(user=self.user, activo=self.activo, cantidad=2, token=token)
        second = create_internal(user=self.user, activo=self.activo, cantidad=2, token=token)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(OrdenPago.objects.count(), 1)
        with self.assertRaises(ValidationError):
            create_internal(user=self.user, activo=self.activo, cantidad=3, token=token)

    def test_token_is_bound_to_user(self):
        with self.assertRaises(ValidationError):
            create_internal(user=self.other, activo=self.activo, cantidad=2, token=submission_token(self.user, self.activo))

    def test_invalid_quantities(self):
        self.login()
        for quantity in (0, -1, "oops", "1.5", 100001):
            with self.subTest(quantity=quantity):
                response = self.client.post(self.url("checkout"), {"cantidad": quantity, "token": submission_token(self.user, self.activo)})
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].errors)
        self.assertFalse(OrdenPago.objects.exists())

    def test_missing_inactive_and_zero_price(self):
        self.login()
        self.assertEqual(self.client.get("/pagos/checkout/999999/").status_code, 404)
        self.activo.activo = False
        self.activo.save()
        self.assertEqual(self.client.get(self.url("checkout")).status_code, 404)
        self.activo.activo = True
        self.activo.precio_actual = 0
        self.activo.save()
        with self.assertRaises(ValidationError):
            create_internal(user=self.user, activo=self.activo, cantidad=1, token=submission_token(self.user, self.activo))

    def test_ownership_all_order_endpoints(self):
        order = self.order()
        self.client.force_login(self.other)
        for name in ("orden_detalle", "estado", "success", "pending", "failure", "iniciar"):
            with self.subTest(name=name):
                response = self.client.post(self.url(name, order)) if name == "iniciar" else self.client.get(self.url(name, order))
                self.assertEqual(response.status_code, 404)

    def test_private_pages_noindex_and_sitemap_exclusion(self):
        self.login()
        order = self.order()
        for url in (self.url("checkout"), order.get_absolute_url(), reverse("pagos:historial")):
            self.assertContains(self.client.get(url), 'name="robots" content="noindex, follow"')
        self.assertNotContains(self.client.get("/sitemap.xml"), "/pagos/")

    def test_return_pages_and_polling_never_approve(self):
        self.login()
        order = self.order()
        for name in ("success", "pending", "failure", "estado"):
            self.assertEqual(self.client.get(self.url(name, order), {"status": "approved"}).status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.estado, "PENDING")
        self.assertFalse(InversionSimulada.objects.exists())
        self.http_guard.assert_not_called()

    def test_checkout_csrf_required(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(self.url("checkout"), {}).status_code, 403)
        self.assertEqual(client.post(self.url("iniciar", self.order()), {}).status_code, 403)

    def test_start_persists_id_and_url_but_never_credits(self):
        order = self.order()
        order.mp_order_id = None
        order.save()
        client = Mock()
        client.create_order.return_value = remote(order)
        result = start_checkout(order.pk, client)
        self.assertEqual(result.mp_order_id, "ORDTST123")
        self.assertIn("order_id=ORDTST123", result.checkout_url)
        client.create_order.assert_called_once_with(order.checkout_payload, order.idempotency_key)
        self.assertFalse(InversionSimulada.objects.exists())
        start_checkout(order.pk, client)
        self.assertEqual(client.create_order.call_count, 1)

    def test_timeout_retry_same_key_and_payload(self):
        order = self.order()
        order.mp_order_id = None
        order.save()
        client = Mock()
        client.create_order.side_effect = ProviderError()
        with self.assertRaises(ProviderError):
            start_checkout(order.pk, client)
        order.refresh_from_db()
        self.assertEqual(order.estado, "ERROR")
        OrdenPago.objects.filter(pk=order.pk).update(ultimo_intento=timezone.now()-timedelta(minutes=1))
        with override_settings(MERCADOPAGO_DEMO_AMOUNT_ARS="999.00", MERCADOPAGO_PUBLIC_BASE_URL="https://changed.example"):
            with self.assertRaises(ProviderError):
                start_checkout(order.pk, client)
        self.assertEqual(client.create_order.call_args_list[0], client.create_order.call_args_list[1])

    def test_pending(self):
        order = self.order()
        result = PaymentService.apply(order.pk, remote(order, "processing", "in_process"), order.mp_order_id)
        self.assertEqual(result.estado, "PENDING")
        self.assertFalse(InversionSimulada.objects.exists())

    def test_approval_uses_snapshot_once(self):
        order = self.order()
        Producto.objects.filter(pk=self.activo.pk).update(precio_actual=999)
        for _ in range(2):
            result = PaymentService.apply(order.pk, remote(order), order.mp_order_id)
        self.assertEqual(result.estado, "APPROVED")
        self.assertEqual(InversionSimulada.objects.count(), 1)
        self.assertEqual(result.inversion.precio_compra, Decimal("250"))
        self.assertEqual(result.inversion.cantidad, 2)
        self.assertEqual(PagoProveedor.objects.count(), 1)
        self.assertEqual(Notificacion.objects.filter(tipo="compra").count(), 1)

    def test_rejected_cancelled_action_unknown(self):
        for status, detail, expected in [("failed", "high_risk", "REJECTED"), ("canceled", "canceled", "CANCELLED"),
                ("action_required", "waiting_capture", "ACTION_REQUIRED"), ("processed", "unknown", "REVIEW_REQUIRED")]:
            with self.subTest(status=status):
                order = self.order()
                data = remote(order, status, detail)
                data["transactions"] = {}
                result = PaymentService.apply(order.pk, data, order.mp_order_id)
                self.assertEqual(result.estado, expected)
        self.assertFalse(InversionSimulada.objects.exists())

    def test_remote_mismatches_go_to_review(self):
        for key, value in [("id", "OTHER"), ("external_reference", str(uuid.uuid4())), ("total_amount", "1.00"),
                           ("currency", "USD"), ("live_mode", True), ("processing_mode", "automatic"),
                           ("total_paid_amount", "0.00"), ("last_updated_date", None)]:
            with self.subTest(key=key):
                order = self.order()
                data = remote(order)
                data[key] = value
                result = PaymentService.apply(order.pk, data, order.mp_order_id)
                self.assertEqual(result.estado, "REVIEW_REQUIRED")
        self.assertFalse(InversionSimulada.objects.exists())

    def test_payment_association_mismatch(self):
        first = self.order()
        PaymentService.apply(first.pk, remote(first), first.mp_order_id)
        other = self.order()
        result = PaymentService.apply(other.pk, remote(other), other.mp_order_id)
        self.assertEqual(result.estado, "REVIEW_REQUIRED")
        self.assertEqual(InversionSimulada.objects.count(), 1)

    def test_rollback_on_portfolio_failure(self):
        order = self.order()
        with patch("pagos.services.payments.PortfolioService.crear", side_effect=RuntimeError("local failure")):
            with self.assertRaises(RuntimeError):
                PaymentService.apply(order.pk, remote(order), order.mp_order_id)
        order.refresh_from_db()
        self.assertEqual(order.estado, "PENDING")
        self.assertFalse(PagoProveedor.objects.exists())
        self.assertFalse(EventoPago.objects.exists())

    def test_old_update_does_not_downgrade(self):
        order = self.order()
        PaymentService.apply(order.pk, remote(order), order.mp_order_id)
        result = PaymentService.apply(order.pk, remote(order, "processing", "in_process", "2026-09-29T12:00:00Z"), order.mp_order_id)
        self.assertEqual(result.estado, "APPROVED")

    def test_refund_deactivates_keeps_history(self):
        order = self.order()
        PaymentService.apply(order.pk, remote(order), order.mp_order_id)
        result = PaymentService.apply(order.pk, remote(order, "processed", "refunded", "2026-10-01T12:00:00Z"), order.mp_order_id)
        self.assertEqual(result.estado, "REFUNDED")
        self.assertFalse(InversionSimulada.objects.get().activa)
        result = PaymentService.apply(order.pk, remote(order, date="2026-10-02T12:00:00Z"), order.mp_order_id)
        self.assertEqual(result.estado, "REFUNDED")
        self.assertFalse(InversionSimulada.objects.get().activa)
        self.login()
        dashboard = self.client.get(reverse("dashboard"))
        self.assertEqual(dashboard.context["cantidad_inversiones"], 0)
        self.assertEqual(InversionSimulada.objects.count(), 1)

    def test_partial_refund_and_chargeback_review(self):
        for chargeback in (False, True):
            order = self.order()
            data = remote(order, "processed", "partially_refunded")
            data["transactions"] = {"chargebacks": [{"id": "CBK123"}]} if chargeback else {}
            result = PaymentService.apply(order.pk, data, order.mp_order_id)
            self.assertEqual(result.estado, "REVIEW_REQUIRED")

    def webhook(self, order, signature=True, body_id=None):
        rid, ts = "request-123", "1742505638683"
        manifest = f"id:{order.mp_order_id};request-id:{rid};ts:{ts};"
        digest = hmac.new(CONFIG["MERCADOPAGO_WEBHOOK_SECRET"].encode(), manifest.encode(), hashlib.sha256).hexdigest()
        headers = {"HTTP_X_REQUEST_ID": rid}
        if signature:
            headers["HTTP_X_SIGNATURE"] = f"ts={ts},v1={digest}"
        return self.client.post(reverse("pagos:webhook") + f"?data.id={order.mp_order_id}&type=order",
            data=json.dumps({"type": "order", "data": {"id": body_id or order.mp_order_id}}), content_type="application/json", **headers)

    def test_webhook_missing_signature(self):
        self.assertEqual(self.webhook(self.order(), signature=False).status_code, 401)
        self.http_guard.assert_not_called()

    def test_webhook_invalid_signature(self):
        response = self.client.post(reverse("pagos:webhook")+"?data.id=ORDTST123", "{}", content_type="application/json",
            HTTP_X_REQUEST_ID="request-123", HTTP_X_SIGNATURE="ts=123,v1="+"0"*64)
        self.assertEqual(response.status_code, 401)

    def test_webhook_query_body_mismatch(self):
        self.assertEqual(self.webhook(self.order(), body_id="OTHER").status_code, 400)
        self.http_guard.assert_not_called()

    def test_webhook_valid_duplicate(self):
        order = self.order()
        with patch("pagos.services.webhook.MercadoPagoClient.get_order", return_value=remote(order)) as get:
            self.assertEqual(self.webhook(order).status_code, 200)
            self.assertEqual(self.webhook(order).status_code, 200)
            self.assertEqual(get.call_count, 2)
        self.assertEqual(InversionSimulada.objects.count(), 1)

    def test_webhook_transient_error(self):
        order = self.order()
        with patch("pagos.services.webhook.MercadoPagoClient.get_order", side_effect=ProviderError()):
            self.assertEqual(self.webhook(order).status_code, 503)

    def test_reconciliation(self):
        order = self.order()
        with patch("pagos.services.payments.MercadoPagoClient.get_order", return_value=remote(order)):
            output = io.StringIO()
            call_command("reconciliar_pagos", stdout=output)
        self.assertIn("Conciliadas: 1", output.getvalue())
        self.assertEqual(InversionSimulada.objects.count(), 1)

    def test_http_client_timeout_and_headers(self):
        client = MercadoPagoClient()
        with patch("pagos.services.mercado_pago.requests.request", return_value=Mock(status_code=201, json=lambda: {"id": "ORDTST123"})) as request:
            client.create_order({"type": "online"}, "stable-key")
            self.assertEqual(request.call_args.args, ("POST", "https://api.mercadopago.com/v1/orders"))
            self.assertEqual(request.call_args.kwargs["headers"]["X-Idempotency-Key"], "stable-key")
            self.assertEqual(request.call_args.kwargs["timeout"], (3, 7))
            self.assertFalse(request.call_args.kwargs["allow_redirects"])
        with patch("pagos.services.mercado_pago.requests.request", side_effect=requests.Timeout("secret")):
            with self.assertRaises(ProviderError) as error:
                client.get_order("ORDTST123")
            self.assertNotIn("secret", str(error.exception))

    def test_configuration_disabled_and_invalid(self):
        self.login()
        with override_settings(MERCADOPAGO_ENABLED=False):
            self.assertEqual(self.client.get(self.url("checkout")).status_code, 503)
        for values in ({"MERCADOPAGO_ENVIRONMENT": "production"}, {"MERCADOPAGO_ACCESS_TOKEN": "APP_USR-fake"},
                       {"MERCADOPAGO_DEMO_AMOUNT_ARS": ""}, {"MERCADOPAGO_DEMO_AMOUNT_ARS": "0"},
                       {"MERCADOPAGO_DEMO_AMOUNT_ARS": "NaN"}, {"MERCADOPAGO_PUBLIC_BASE_URL": "http://localhost"}):
            with self.subTest(values=values), override_settings(**values), self.assertRaises(ImproperlyConfigured):
                payment_config()

    def test_free_simulation_preserved(self):
        self.login()
        response = self.client.post(reverse("comprar_activo", kwargs={"activo_id": self.activo.pk}), {"cantidad": "invalid"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(InversionSimulada.objects.get().cantidad, 1)
        self.assertFalse(OrdenPago.objects.exists())


    def test_webhook_is_only_csrf_exemption(self):
        from pagos import views
        self.assertTrue(views.mercadopago_webhook.csrf_exempt)
        self.assertFalse(getattr(views.checkout, "csrf_exempt", False))
        self.assertFalse(getattr(views.iniciar, "csrf_exempt", False))
        self.assertEqual(self.client.get(reverse("pagos:webhook")).status_code, 405)

    def test_webhook_pending_rejected_and_cancelled(self):
        for status, detail, expected in [("processing", "in_process", "PENDING"),
                ("failed", "high_risk", "REJECTED"), ("canceled", "canceled", "CANCELLED")]:
            with self.subTest(status=status):
                order = self.order()
                data = remote(order, status, detail)
                data["transactions"] = {}
                with patch("pagos.services.webhook.MercadoPagoClient.get_order", return_value=data):
                    self.assertEqual(self.webhook(order).status_code, 200)
                order.refresh_from_db()
                self.assertEqual(order.estado, expected)
        self.assertFalse(InversionSimulada.objects.exists())

    def test_webhook_before_create_response(self):
        order = self.order()
        data = remote(order)
        OrdenPago.objects.filter(pk=order.pk).update(mp_order_id=None, ultimo_intento=timezone.now())
        with patch("pagos.services.webhook.MercadoPagoClient.get_order", return_value=data):
            self.assertEqual(self.webhook(order).status_code, 200)
        self.assertEqual(InversionSimulada.objects.count(), 1)

    def test_provider_creation_bad_redirect_is_blocked(self):
        order = self.order()
        order.mp_order_id = None
        order.save()
        data = remote(order)
        data["checkout_url"] = "https://attacker.example/"
        client = Mock(create_order=Mock(return_value=data))
        with self.assertRaises(ProviderError):
            start_checkout(order.pk, client)
        order.refresh_from_db()
        self.assertEqual(order.estado, "REVIEW_REQUIRED")
        self.assertFalse(order.checkout_url)

    def test_context_seller_application_change(self):
        for field in ("seller", "application"):
            order = self.order()
            order.mp_user_id = "123"
            order.mp_application_id = "456"
            order.save()
            data = remote(order)
            data["transactions"] = {}
            if field == "seller":
                data["user_id"] = "999"
            else:
                data["integration_data"]["application_id"] = "999"
            result = PaymentService.apply(order.pk, data, order.mp_order_id)
            self.assertEqual(result.estado, "REVIEW_REQUIRED")

    def test_no_sensitive_payload_is_persisted(self):
        order = self.order()
        data = remote(order)
        data["payer"] = {"email": "sensitive@example.com"}
        data["transactions"]["payments"][0]["payment_method"] = {"token": "SENSITIVE-CARD-TOKEN"}
        PaymentService.apply(order.pk, data, order.mp_order_id)
        content = json.dumps(list(OrdenPago.objects.values()), default=str) + json.dumps(list(PagoProveedor.objects.values()), default=str) + json.dumps(list(EventoPago.objects.values()), default=str)
        self.assertNotIn("SENSITIVE", content)
        self.assertNotIn("sensitive@example", content)

    def test_refund_before_approval_does_not_create_position(self):
        order = self.order()
        result = PaymentService.apply(order.pk, remote(order, "refunded", "refunded"), order.mp_order_id)
        self.assertEqual(result.estado, "REFUNDED")
        self.assertFalse(InversionSimulada.objects.exists())

    def test_review_is_not_automatically_cleared(self):
        order = self.order()
        PaymentService.apply(order.pk, remote(order, "processed", "partially_refunded"), order.mp_order_id)
        result = PaymentService.apply(order.pk, remote(order, date="2026-10-01T12:00:00Z"), order.mp_order_id)
        self.assertEqual(result.estado, "REVIEW_REQUIRED")
        self.assertFalse(InversionSimulada.objects.exists())

    def test_reconcile_skips_created_and_terminal(self):
        for state in ("CREATED", "APPROVED", "REFUNDED", "REVIEW_REQUIRED", "CANCELLED", "REJECTED"):
            order = self.order()
            order.estado = state
            order.save()
        with patch("pagos.services.payments.MercadoPagoClient.get_order") as get:
            call_command("reconciliar_pagos", stdout=io.StringIO())
            get.assert_not_called()

    def test_readonly_admin(self):
        from pagos.admin import OrdenPagoAdmin
        from django.contrib.admin import site
        admin = OrdenPagoAdmin(OrdenPago, site)
        self.assertFalse(admin.has_add_permission(None))
        self.assertFalse(admin.has_change_permission(None, self.order()))
        self.assertFalse(admin.has_delete_permission(None))

    def test_database_constraints(self):
        from django.db import IntegrityError, transaction
        order = self.order()
        for values in ({"cantidad": 0}, {"importe_demo": 0}, {"environment": "production"}, {"moneda_cobro": "USD"}):
            with self.subTest(values=values), self.assertRaises(IntegrityError), transaction.atomic():
                OrdenPago.objects.filter(pk=order.pk).update(**values)

    def test_real_http_is_blocked(self):
        with self.assertRaisesRegex(AssertionError, "HTTP REAL PROHIBIDO"):
            MercadoPagoClient().get_order("ORDTST123")


@override_settings(**CONFIG)
class ConcurrentPaymentTests(OfflineMixin, TransactionTestCase):
    @skipUnlessDBFeature("has_select_for_update")
    def test_concurrent_approvals_exactly_one_investment(self):
        self.user = get_user_model().objects.create_user(username="concurrent")
        self.activo = Producto.objects.create(nombre="Apple", simbolo="AAPL", precio_actual=250, moneda="USD")
        order = self.order()
        barrier = threading.Barrier(2)
        def apply():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                PaymentService.apply(order.pk, remote(order), order.mp_order_id)
            finally:
                connection.close()
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(apply) for _ in range(2)]
            for future in futures:
                future.result(timeout=20)
        self.assertEqual(InversionSimulada.objects.count(), 1)
        self.assertEqual(PagoProveedor.objects.count(), 1)

    @skipUnlessDBFeature("has_select_for_update")
    def test_concurrent_internal_submissions(self):
        self.user = get_user_model().objects.create_user(username="submitter")
        self.activo = Producto.objects.create(nombre="Apple", simbolo="AAPL", precio_actual=250, moneda="USD")
        token = submission_token(self.user, self.activo)
        barrier = threading.Barrier(2)
        def create():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return create_internal(user=self.user, activo=self.activo, cantidad=2, token=token).pk
            finally:
                connection.close()
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(create) for _ in range(2)]
            ids = [future.result(timeout=20) for future in futures]
        self.assertEqual(ids[0], ids[1])
        self.assertEqual(OrdenPago.objects.count(), 1)
