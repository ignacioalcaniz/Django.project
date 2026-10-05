from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from django.test import TestCase, SimpleTestCase, Client
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle

from api.permissions import ProductoPermission
from api.serializers import ProductoSerializer
from vistaprevia.admin import ProductoAdmin
from vistaprevia.models import Producto, CotizacionHistorica
from vistaprevia.services.analytics import HistoricalAnalyticsService
from vistaprevia.services.score_sync import QuantEdgeScoreSyncService
from vistaprevia.services.market_sync import MarketDataSyncService
from vistaprevia.services.historical_sync import HistoricalMarketDataService
from usuarios.models import InversionSimulada


def history(product, count=60):
    start = timezone.now() - timedelta(days=100)
    return CotizacionHistorica.objects.bulk_create([
        CotizacionHistorica(activo=product, fecha_hora=start+timedelta(days=i),
            apertura=100+i, maximo=102+i, minimo=99+i, cierre=101+i, volumen=10000)
        for i in range(count)])


class QuantitativeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.product = Producto.objects.create(nombre="Demo", simbolo="DEM", precio_actual=160)
        cls.empty = Producto.objects.create(nombre="Empty", simbolo="EMPTY")
        cls.inactive = Producto.objects.create(nombre="Hidden", simbolo="HID", activo=False)
        cls.bars = history(cls.product)
        cls.staff = get_user_model().objects.create_superuser(username="quant-admin", email="fake@example.com", password=None)

    def setUp(self):
        self.client = APIClient()
        cache.clear()
        guard = patch("requests.sessions.Session.request", side_effect=AssertionError("HTTP forbidden"))
        guard.start()
        self.addCleanup(guard.stop)

    def endpoint(self, action, product=None):
        return reverse("api:activo-"+action, args=[(product or self.product).pk])

    def test_missing_and_inactive_quantitative_endpoints(self):
        for action in ("historico", "analytics", "score"):
            for pk in (999999, self.inactive.pk):
                with self.subTest(action=action, pk=pk):
                    self.assertEqual(self.client.get(reverse("api:activo-"+action, args=[pk])).status_code, 404)

    def test_historical_latest_window_is_chronological(self):
        response = self.client.get(self.endpoint("historico"), {"limite": 3})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 3)
        dates = [row["fecha_hora"] for row in response.data["results"]]
        self.assertEqual(dates, sorted(dates))
        self.assertEqual([row["id"] for row in response.data["results"]], [row.pk for row in self.bars[-3:]])

    def test_limits_are_consistent(self):
        for action in ("historico", "analytics", "score"):
            for value in ("abc", "-1", "0", "999999", "501", "1.5", ""):
                with self.subTest(action=action, value=value):
                    self.assertEqual(self.client.get(self.endpoint(action), {"limite": value}).status_code, 400)
            for value in (1, 500):
                self.assertEqual(self.client.get(self.endpoint(action), {"limite": value}).status_code, 200)
        response = self.client.get(self.endpoint("analytics"), {"limite": 1})
        self.assertEqual(response.data["configuracion"]["observaciones"], 1)

    def test_unsupported_intervals(self):
        for action in ("historico", "analytics", "score"):
            with self.subTest(action=action):
                self.assertEqual(self.client.get(self.endpoint(action), {"intervalo": "unsupported"}).status_code, 400)
        for action in ("analytics", "score"):
            self.assertEqual(self.client.get(self.endpoint(action), {"intervalo": "1h"}).status_code, 400)

    def test_analytics_sufficient_and_empty(self):
        data = self.client.get(self.endpoint("analytics")).data
        self.assertEqual(data["configuracion"]["observaciones"], 60)
        self.assertIsNotNone(data["indicadores"]["sma_50"])
        self.assertEqual(data["indicadores"]["rsi_14"], 100)
        data = self.client.get(self.endpoint("analytics", self.empty)).data
        self.assertEqual(data["configuracion"]["observaciones"], 0)
        self.assertIsNone(data["indicadores"]["sma_20"])

    def test_score_sufficient_and_insufficient(self):
        data = self.client.get(self.endpoint("score")).data
        self.assertGreater(len(data["score_actual"]["componentes"]), 0)
        self.assertFalse(data["sincronizado"])
        data = self.client.get(self.endpoint("score", self.empty)).data
        self.assertEqual(data["score_actual"]["recomendacion"], "Datos insuficientes")
        self.assertFalse(data["sincronizado"])

    def test_score_snapshot_compares_all_fields(self):
        QuantEdgeScoreSyncService().sincronizar_activo(self.product)
        self.assertTrue(self.client.get(self.endpoint("score")).data["sincronizado"])
        changes = {"puntaje_quant": 0, "recomendacion": "vender", "cobertura_datos_quant": 1,
                   "version_score_quant": "obsolete", "fecha_ultimo_score_quant": None}
        for field, value in changes.items():
            with self.subTest(field=field):
                QuantEdgeScoreSyncService().sincronizar_activo(self.product)
                Producto.objects.filter(pk=self.product.pk).update(**{field: value})
                self.assertFalse(self.client.get(self.endpoint("score")).data["sincronizado"])

    def test_old_snapshot_date_is_not_synchronized(self):
        QuantEdgeScoreSyncService().sincronizar_activo(self.product)
        Producto.objects.filter(pk=self.product.pk).update(fecha_ultimo_score_quant=timezone.now()-timedelta(days=1))
        self.assertFalse(self.client.get(self.endpoint("score")).data["sincronizado"])

    def test_ranking_stable_paginated(self):
        stamp = timezone.now()
        products = [Producto.objects.create(nombre="Tie", simbolo=f"T{i}", puntaje_quant=90,
                        cobertura_datos_quant=95, fecha_ultimo_score_quant=stamp) for i in range(23)]
        first = self.client.get(reverse("api:ranking"))
        second = self.client.get(reverse("api:ranking"), {"page": 2})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.data["count"], 23)
        self.assertEqual(len(first.data["results"]), 20)
        self.assertTrue(first.data["next"])
        ids = [row["id"] for row in first.data["results"]+second.data["results"]]
        self.assertEqual(ids, [p.pk for p in products])
        self.assertIsNone(second.data["next"])
        self.assertEqual(self.client.get(reverse("api:ranking"), {"page": 99}).status_code, 404)

    def test_throttling_is_scoped(self):
        with patch.object(ScopedRateThrottle, "THROTTLE_RATES", {"quantitative": "2/min"}):
            self.assertEqual(self.client.get(self.endpoint("analytics")).status_code, 200)
            self.assertEqual(self.client.get(self.endpoint("score")).status_code, 200)
            response = self.client.get(self.endpoint("historico"))
            self.assertEqual(response.status_code, 429)
            self.assertIn("Retry-After", response)
            self.assertEqual(self.client.get(reverse("api:ranking")).status_code, 200)

    def test_throttle_cannot_be_evaded_with_forwarded_header(self):
        with patch.object(ScopedRateThrottle, "THROTTLE_RATES", {"quantitative": "1/min"}):
            self.assertEqual(self.client.get(self.endpoint("score"), HTTP_X_FORWARDED_FOR="1.1.1.1").status_code, 200)
            self.assertEqual(self.client.get(self.endpoint("score"), HTTP_X_FORWARDED_FOR="2.2.2.2").status_code, 429)

    def test_delete_never_authorized_and_returns_405(self):
        for user in (None, self.staff):
            self.client.force_authenticate(user=user)
            self.assertEqual(self.client.delete(reverse("api:activo-detail", args=[self.product.pk])).status_code, 405)
        request = SimpleNamespace(method="DELETE", user=self.staff)
        self.assertFalse(ProductoPermission().has_permission(request, None))
        self.assertTrue(Producto.objects.filter(pk=self.product.pk).exists())

    def test_52week_create_defaults_negative_and_range(self):
        for values in ({"minimo_52_semanas": "1"}, {"minimo_52_semanas": "-1"},
                       {"maximo_52_semanas": "-1"}, {"minimo_52_semanas": "5", "maximo_52_semanas": "4"}):
            with self.subTest(values=values):
                serializer = ProductoSerializer(data={"nombre": "New", "simbolo": "NEW", **values})
                self.assertFalse(serializer.is_valid())
        for values in ({}, {"minimo_52_semanas": "0", "maximo_52_semanas": "0"}, {"maximo_52_semanas": "10"}):
            self.assertTrue(ProductoSerializer(data={"nombre": "New", "simbolo": "NEW", **values}).is_valid())

    def test_writable_decimals_reject_nonfinite(self):
        for value in ("NaN", "Infinity", "-Infinity"):
            serializer = ProductoSerializer(self.product, data={"precio_objetivo": value}, partial=True)
            self.assertFalse(serializer.is_valid())

    def test_activation_requires_prepared_market_data(self):
        self.client.force_authenticate(self.staff)
        url = reverse("api:activo-detail", args=[self.inactive.pk])
        self.assertEqual(self.client.patch(url, {"activo": True}, format="json").status_code, 400)
        Producto.objects.filter(pk=self.inactive.pk).update(precio_actual=10, estado_sincronizacion="sincronizado", fecha_ultima_sincronizacion=timezone.now())
        self.assertEqual(self.client.patch(url, {"activo": True}, format="json").status_code, 200)

    def test_create_then_trivial_activation_is_blocked(self):
        self.client.force_authenticate(self.staff)
        response = self.client.post(reverse("api:activo-list"),
            {"nombre": "New", "simbolo": "NEW", "activo": True, "precio_actual": "10", "estado_sincronizacion": "sincronizado"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.data["activo"])
        url = reverse("api:activo-detail", args=[response.data["id"]])
        self.assertEqual(self.client.patch(url, {"activo": True}, format="json").status_code, 400)

    def test_admin_derived_fields_readonly(self):
        model_admin = ProductoAdmin(Producto, admin.site)
        for field in ("puntaje_quant", "recomendacion", "cobertura_datos_quant", "fecha_ultimo_score_quant", "version_score_quant"):
            self.assertIn(field, model_admin.readonly_fields)
        self.assertIn("recalcular_scores_quant", model_admin.actions)

    def test_strict_mode_connection(self):
        if connection.vendor != "mysql":
            self.skipTest("MySQL/MariaDB only")
        with connection.cursor() as cursor:
            cursor.execute("SELECT @@SESSION.sql_mode")
            self.assertIn("STRICT_TRANS_TABLES", cursor.fetchone()[0])

    def test_market_nonfinite_never_persisted_and_inactive_preparation(self):
        quote = SimpleNamespace(price=Decimal("NaN"), open_price=10, previous_close=10, high=10, low=10,
                                percent_change=0, volume=100, exchange="", currency="USD")
        service = MarketDataSyncService(client=Mock(get_quote=Mock(return_value=quote)))
        result = service.sincronizar_activo(self.inactive, force=True)
        self.assertFalse(result.success)
        quote.price = Decimal("10")
        result = service.sincronizar_activo(self.inactive, force=True)
        self.assertTrue(result.success)
        self.inactive.refresh_from_db()
        self.assertFalse(self.inactive.activo)
        self.assertEqual(self.inactive.precio_actual, 10)

    def test_historical_explicit_preparation_does_not_publish(self):
        bar = SimpleNamespace(datetime=timezone.now(), open_price=10, high=10, low=10, close=10, volume=1)
        client = Mock(get_time_series=Mock(return_value=[bar]))
        service = HistoricalMarketDataService(client=client)
        self.assertFalse(service.sincronizar_activo(self.inactive).success)
        client.get_time_series.assert_not_called()
        self.assertTrue(service.sincronizar_activo(self.inactive, force=True).success)
        self.inactive.refresh_from_db()
        self.assertFalse(self.inactive.activo)

    def test_historical_nonfinite_batch_not_persisted(self):
        bar = SimpleNamespace(datetime=timezone.now(), open_price=10, high=10, low=10, close=Decimal("Infinity"), volume=1)
        service = HistoricalMarketDataService(client=Mock(get_time_series=Mock(return_value=[bar])))
        self.assertFalse(service.sincronizar_activo(self.empty).success)
        self.assertFalse(self.empty.cotizaciones_historicas.exists())

    def test_portfolio_excludes_inactive_and_history_keeps_it(self):
        InversionSimulada.objects.create(usuario=self.staff, activo=self.product, cantidad=2, precio_compra=10, activa=True)
        InversionSimulada.objects.create(usuario=self.staff, activo=self.product, cantidad=100, precio_compra=10, activa=False)
        self.client.force_login(self.staff)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.context["cantidad_inversiones"], 1)
        self.assertEqual(response.context["total_invertido"], 20)
        profile = self.client.get(reverse("perfil_usuario"))
        self.assertEqual(profile.context["inversiones"].count(), 2)

    def test_favorite_external_redirect_blocked(self):
        self.client.force_login(self.staff)
        response = self.client.post(reverse("alternar_favorito", args=[self.product.pk]), {"next": "https://attacker.example"})
        self.assertEqual(response.url, reverse("dashboard"))

    def test_logout_requires_post_and_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.staff)
        self.assertEqual(client.get(reverse("cerrar_sesion")).status_code, 405)
        self.assertEqual(client.post(reverse("cerrar_sesion")).status_code, 403)


class AnalyticsEdgeTests(SimpleTestCase):
    def test_rsi_flat_up_and_down(self):
        calculate = HistoricalAnalyticsService._calculate_rsi
        self.assertEqual(calculate([10.0]*20), 50)
        self.assertEqual(calculate(list(range(1, 21))), 100)
        self.assertEqual(calculate(list(range(20, 0, -1))), 0)
        self.assertIsNone(calculate([1]*14))

    def test_score_normalization_rejects_nonfinite(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.assertRaises(ValueError):
                QuantEdgeScoreSyncService._normalizar_porcentaje(value)
