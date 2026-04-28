import pytest
from unittest.mock import patch, MagicMock
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


@pytest.fixture
def api_response_communes():
    return {
        "total": 50,
        "page": 1,
        "limit": 25,
        "data": [
            {"code_insee": "59009", "city": "Armentières"},
            {"code_insee": "59350", "city": "Lille"},
        ],
    }


@pytest.fixture
def api_response_vide():
    return {"total": 0, "page": 1, "limit": 25, "data": []}


# ============================================================
# SERVICES — DetailService
# ============================================================

class TestDetailService:

    @patch("detail.services.requests.get")
    def test_succes_retourne_donnees(self, mock_get, api_response_communes):
        """Retourne les données JSON si l'API répond 200."""
        from detail.services import DetailService
        mock_get.return_value = MagicMock(status_code=200, json=lambda: api_response_communes)

        service = DetailService()
        result = service.get_detail_communes()

        assert result["total"] == 50
        assert len(result["data"]) == 2

    @patch("detail.services.requests.get")
    def test_erreur_api_retourne_defaut(self, mock_get):
        """Retourne un dict vide par défaut si l'API ne répond pas 200."""
        from detail.services import DetailService
        mock_get.return_value = MagicMock(status_code=500)

        service = DetailService()
        result = service.get_detail_communes()

        assert result["total"] == 0
        assert result["data"] == []

    @patch("detail.services.requests.get")
    def test_exception_retourne_defaut(self, mock_get):
        """Retourne un dict vide par défaut si une exception est levée."""
        from detail.services import DetailService
        mock_get.side_effect = Exception("Timeout")

        service = DetailService()
        result = service.get_detail_communes()

        assert result["total"] == 0
        assert result["data"] == []

    @patch("detail.services.requests.get")
    def test_limit_max_100(self, mock_get, api_response_communes):
        """La limite est plafonnée à 100 même si on passe 200."""
        from detail.services import DetailService
        mock_get.return_value = MagicMock(status_code=200, json=lambda: api_response_communes)

        service = DetailService()
        service.get_detail_communes(limit=200)

        # Vérification que l'URL appelée contient limit=100 max
        called_url = mock_get.call_args[0][0]
        assert "limit=100" in called_url

    @patch("detail.services.requests.get")
    def test_pagination_skip_calcule(self, mock_get, api_response_communes):
        """Le skip est bien calculé à partir de la page et la limite."""
        from detail.services import DetailService
        mock_get.return_value = MagicMock(status_code=200, json=lambda: api_response_communes)

        service = DetailService()
        service.get_detail_communes(page=3, limit=25)

        called_url = mock_get.call_args[0][0]
        assert "skip=50" in called_url  # (3-1) * 25 = 50

    @patch("detail.services.requests.get")
    def test_recherche_passee_en_parametre(self, mock_get, api_response_communes):
        """Le terme de recherche est bien transmis à l'API."""
        from detail.services import DetailService
        mock_get.return_value = MagicMock(status_code=200, json=lambda: api_response_communes)

        service = DetailService()
        service.get_detail_communes(search="Lille")

        called_params = mock_get.call_args[1]["params"]
        assert called_params.get("search") == "Lille"


# ============================================================
# VIEWS — DetailView
# ============================================================

@pytest.mark.django_db
class TestDetailView:

    def test_acces_non_connecte_redirige(self, client):
        """Un utilisateur non connecté est redirigé vers le login."""
        response = client.get(reverse("detail"))
        assert response.status_code == 302
        assert "/home" in response["Location"]

    @patch("detail.views.DetailService.get_detail_communes")
    def test_acces_connecte_200(self, mock_service, authenticated_client, api_response_communes):
        """Un utilisateur connecté accède à la page (200)."""
        mock_service.return_value = api_response_communes

        response = authenticated_client.get(reverse("detail"))
        assert response.status_code == 200

    @patch("detail.views.DetailService.get_detail_communes")
    def test_valeurs_par_defaut(self, mock_service, authenticated_client, api_response_communes):
        """Sans paramètres, page=1 et limit=25 par défaut."""
        mock_service.return_value = api_response_communes

        response = authenticated_client.get(reverse("detail"))
        assert response.context["current_page"] == 1
        assert response.context["limit"] == 25

    @patch("detail.views.DetailService.get_detail_communes")
    def test_pagination_total_pages(self, mock_service, authenticated_client):
        """total_pages est correctement calculé."""
        mock_service.return_value = {"total": 100, "page": 1, "limit": 25, "data": []}

        response = authenticated_client.get(reverse("detail"))
        assert response.context["total_pages"] == 4  # 100 / 25

    @patch("detail.views.DetailService.get_detail_communes")
    def test_pagination_total_items_zero(self, mock_service, authenticated_client, api_response_vide):
        """Si total=0, total_pages vaut 1 (pas de division par zéro)."""
        mock_service.return_value = api_response_vide

        response = authenticated_client.get(reverse("detail"))
        assert response.context["total_pages"] == 1

    @patch("detail.views.DetailService.get_detail_communes")
    def test_has_next_et_has_prev(self, mock_service, authenticated_client):
        """has_next et has_prev sont corrects selon la page courante."""
        mock_service.return_value = {"total": 100, "page": 2, "limit": 25, "data": []}

        response = authenticated_client.get(reverse("detail"), {"page": "2"})
        assert response.context["has_next"] is True
        assert response.context["has_prev"] is True

    @patch("detail.views.DetailService.get_detail_communes")
    def test_premiere_page_pas_de_prev(self, mock_service, authenticated_client):
        """Sur la première page, has_prev est False."""
        mock_service.return_value = {"total": 100, "page": 1, "limit": 25, "data": []}

        response = authenticated_client.get(reverse("detail"), {"page": "1"})
        assert response.context["has_prev"] is False

    @patch("detail.views.DetailService.get_detail_communes")
    def test_derniere_page_pas_de_next(self, mock_service, authenticated_client):
        """Sur la dernière page, has_next est False."""
        mock_service.return_value = {"total": 25, "page": 1, "limit": 25, "data": []}

        response = authenticated_client.get(reverse("detail"), {"page": "1"})
        assert response.context["has_next"] is False

    @patch("detail.views.DetailService.get_detail_communes")
    def test_recherche_transmise_au_contexte(self, mock_service, authenticated_client, api_response_communes):
        """Le terme de recherche est bien dans le contexte."""
        mock_service.return_value = api_response_communes

        response = authenticated_client.get(reverse("detail"), {"search": "Lille"})
        assert response.context["search_query"] == "Lille"

    @patch("detail.views.DetailService.get_detail_communes")
    def test_limit_options_dans_contexte(self, mock_service, authenticated_client, api_response_communes):
        """Les options de limite sont bien dans le contexte."""
        mock_service.return_value = api_response_communes

        response = authenticated_client.get(reverse("detail"))
        assert response.context["limit_options"] == [25, 50, 100]