import pytest
from django.contrib.auth.models import User


@pytest.mark.django_db
def test_registro_page_loads(client):
    response = client.get("/usuarios/registro/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_dashboard_requires_login(client):
    response = client.get("/usuarios/dashboard/")
    assert response.status_code == 302
    assert "/accounts/login/" in response.url


@pytest.mark.django_db
def test_logged_user_can_access_dashboard(client):
    user = User.objects.create_user(
        username="nacho",
        email="nacho@test.com",
        password="testpass123"
    )

    client.login(username="nacho", password="testpass123")

    response = client.get("/usuarios/dashboard/")
    assert response.status_code == 200