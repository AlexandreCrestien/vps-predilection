import pytest
from django.test import Client
from django.urls import reverse
from users.models import CustomUser


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def client():
    return Client()


@pytest.fixture
def user(db):
    return CustomUser.objects.create_user(
        username="test@example.com",
        email="test@example.com",
        password="StrongPass123!",
    )


@pytest.fixture
def authenticated_client(client, user):
    client.login(username="test@example.com", password="StrongPass123!")
    return client


# ============================================================
# VIEWS — AccueilView
# ============================================================

@pytest.mark.django_db
class TestAccueilView:

    def test_acces_connecte_200(self, authenticated_client):
        """Un utilisateur connecté accède à la page d'accueil (200)."""
        response = authenticated_client.get(reverse("home"))
        assert response.status_code == 200

    def test_bon_template_utilise(self, authenticated_client):
        """La vue utilise bien le template home.html."""
        response = authenticated_client.get(reverse("home"))
        assert "home.html" in [t.name for t in response.templates]

    def test_acces_non_connecte(self, client):
        """Un utilisateur non connecté peut accéder à la page (pas de LoginRequired)."""
        response = client.get(reverse("home"))
        assert response.status_code == 200