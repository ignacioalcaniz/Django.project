import pytest
from vistaprevia.models import Producto


@pytest.mark.django_db
def test_crear_producto_activo():
    producto = Producto.objects.create(
        nombre="Apple Inc.",
        simbolo="AAPL",
        descripcion="Empresa tecnológica líder.",
        precio_actual=212.35,
        variacion_diaria=1.22,
        riesgo="medio",
        recomendacion="comprar",
        puntaje_quant=87,
        activo=True,
        es_destacado=True,
    )

    assert producto.nombre == "Apple Inc."
    assert producto.simbolo == "AAPL"
    assert producto.precio_actual == 212.35
    assert producto.activo is True


@pytest.mark.django_db
def test_str_producto():
    producto = Producto.objects.create(
        nombre="Nvidia Corp.",
        simbolo="NVDA",
        precio_actual=920.55,
    )

    assert str(producto) == "NVDA - Nvidia Corp."