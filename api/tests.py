from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from vistaprevia.models import Producto


User = get_user_model()


class ProductoAPITests(APITestCase):
    def setUp(self):
        self.producto = Producto.objects.create(
            nombre="Apple Inc.",
            simbolo="AAPL",
            ticker_externo="AAPL",
            descripcion="Activo de prueba.",
            tipo_activo="accion",
            sector="Tecnología",
            industria="Hardware",
            pais="Estados Unidos",
            bolsa="NASDAQ",
            moneda="USD",
            precio_actual=200,
            precio_objetivo=230,
            riesgo="medio",
            recomendacion="comprar",
            puntaje_quant=77,
            cobertura_datos_quant=95,
            version_score_quant="v1",
            estado_sincronizacion="sincronizado",
            activo=True,
        )

        self.list_url = reverse(
            "api:activo-list"
        )

        self.detail_url = reverse(
            "api:activo-detail",
            args=[self.producto.pk],
        )

        self.staff_sin_permisos = User.objects.create_user(
            username="staff_sin_permisos",
            password="test-password-123",
            is_staff=True,
        )

        self.admin = User.objects.create_user(
            username="admin_api",
            password="test-password-123",
            is_staff=True,
        )

        permisos = Permission.objects.filter(
            content_type__app_label="vistaprevia",
            content_type__model="producto",
            codename__in=[
                "add_producto",
                "change_producto",
            ],
        )

        self.admin.user_permissions.set(permisos)

    def test_anonimo_puede_listar_activos(self):
        response = self.client.get(
            self.list_url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_anonimo_puede_consultar_detalle(self):
        response = self.client.get(
            self.detail_url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["simbolo"],
            "AAPL",
        )

    def test_anonimo_no_puede_crear_activo(self):
        response = self.client.post(
            self.list_url,
            {
                "nombre": "Microsoft Corporation",
                "simbolo": "MSFT",
                "ticker_externo": "MSFT",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_staff_sin_permiso_no_puede_crear_activo(self):
        self.client.force_authenticate(
            user=self.staff_sin_permisos
        )

        response = self.client.post(
            self.list_url,
            {
                "nombre": "Microsoft Corporation",
                "simbolo": "MSFT",
                "ticker_externo": "MSFT",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_admin_con_permiso_puede_crear_activo(self):
        self.client.force_authenticate(
            user=self.admin
        )

        response = self.client.post(
            self.list_url,
            {
                "nombre": "Microsoft Corporation",
                "simbolo": "MSFT",
                "ticker_externo": "MSFT",
                "tipo_activo": "accion",
                "sector": "Tecnología",
                "industria": "Software",
                "pais": "Estados Unidos",
                "riesgo": "medio",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        producto = Producto.objects.get(
            simbolo="MSFT"
        )

        self.assertFalse(
            producto.activo
        )

    def test_no_se_puede_modificar_simbolo(self):
        self.client.force_authenticate(
            user=self.admin
        )

        response = self.client.patch(
            self.detail_url,
            {
                "simbolo": "MSFT",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.producto.refresh_from_db()

        self.assertEqual(
            self.producto.simbolo,
            "AAPL",
        )

    def test_no_se_puede_modificar_ticker_externo(self):
        self.client.force_authenticate(
            user=self.admin
        )

        response = self.client.patch(
            self.detail_url,
            {
                "ticker_externo": "MSFT",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.producto.refresh_from_db()

        self.assertEqual(
            self.producto.ticker_externo,
            "AAPL",
        )

    def test_recomendacion_es_read_only(self):
        self.client.force_authenticate(
            user=self.admin
        )

        response = self.client.patch(
            self.detail_url,
            {
                "recomendacion": "vender",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.producto.refresh_from_db()

        self.assertEqual(
            self.producto.recomendacion,
            "comprar",
        )

    def test_delete_fisico_esta_deshabilitado(self):
        self.client.force_authenticate(
            user=self.admin
        )

        response = self.client.delete(
            self.detail_url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

        self.assertTrue(
            Producto.objects.filter(
                pk=self.producto.pk
            ).exists()
        )

    def test_admin_puede_desactivar_activo(self):
        self.client.force_authenticate(
            user=self.admin
        )

        response = self.client.patch(
            self.detail_url,
            {
                "activo": False,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.producto.refresh_from_db()

        self.assertFalse(
            self.producto.activo
        )

    def test_publico_no_puede_ver_activo_inactivo(self):
        self.producto.activo = False
        self.producto.save(
            update_fields=["activo"]
        )

        response = self.client.get(
            self.detail_url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_admin_puede_ver_activo_inactivo(self):
        self.producto.activo = False
        self.producto.save(
            update_fields=["activo"]
        )

        self.client.force_authenticate(
            user=self.admin
        )

        response = self.client.get(
            self.detail_url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_precio_objetivo_no_puede_ser_negativo(self):
        self.client.force_authenticate(
            user=self.admin
        )

        response = self.client.patch(
            self.detail_url,
            {
                "precio_objetivo": "-10.00",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_minimo_52_no_puede_superar_maximo_52(self):
        self.client.force_authenticate(
            user=self.admin
        )

        response = self.client.patch(
            self.detail_url,
            {
                "minimo_52_semanas": "300.00",
                "maximo_52_semanas": "200.00",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
