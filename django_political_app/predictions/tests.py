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
def api_response_success():
    """Simule une réponse API valide pour une commune."""
    return {
        "status": "success",
        "code_insee": "59009",
        "prediction": 0.72,
        "annee": 2027,
    }


@pytest.fixture
def communes_response():
    """Simule une réponse API valide pour la recherche de communes."""
    return {
        "data": [
            {"code_insee": "59009", "city": "Armentières"},
            {"code_insee": "59350", "city": "Lille"},
        ]
    }


# ============================================================
# SERVICES — PredictionService
# ============================================================

class TestPredictionService:

    @patch("predictions.services.requests.get")
    def test_get_prediction_commune_succes(self, mock_get, api_response_success):
        """Retourne les données JSON si l'API répond 200."""
        from predictions.services import PredictionService
        mock_get.return_value = MagicMock(status_code=200, json=lambda: api_response_success)

        service = PredictionService()
        result = service.get_prediction_commune("59009")

        assert result is not None
        assert result["status"] == "success"
        assert result["code_insee"] == "59009"

    @patch("predictions.services.requests.get")
    def test_get_prediction_commune_api_erreur(self, mock_get):
        """Retourne None si l'API répond autre chose que 200."""
        from predictions.services import PredictionService
        mock_get.return_value = MagicMock(status_code=404)

        service = PredictionService()
        result = service.get_prediction_commune("99999")

        assert result is None

    @patch("predictions.services.requests.get")
    def test_get_prediction_commune_exception(self, mock_get):
        """Retourne None si une exception est levée (timeout, réseau...)."""
        from predictions.services import PredictionService
        mock_get.side_effect = Exception("Timeout")

        service = PredictionService()
        result = service.get_prediction_commune("59009")

        assert result is None

    @patch("predictions.services.requests.get")
    def test_search_communes_succes(self, mock_get, communes_response):
        """Retourne la liste des communes si l'API répond 200."""
        from predictions.services import PredictionService
        mock_get.return_value = MagicMock(status_code=200, json=lambda: communes_response)

        service = PredictionService()
        result = service.search_communes("Lille")

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["city"] == "Armentières"

    @patch("predictions.services.requests.get")
    def test_search_communes_api_erreur(self, mock_get):
        """Retourne une liste vide si l'API répond autre chose que 200."""
        from predictions.services import PredictionService
        mock_get.return_value = MagicMock(status_code=500)

        service = PredictionService()
        result = service.search_communes("Lille")

        assert result == []

    @patch("predictions.services.requests.get")
    def test_search_communes_exception(self, mock_get):
        """Retourne une liste vide si une exception est levée."""
        from predictions.services import PredictionService
        mock_get.side_effect = Exception("Connexion refusée")

        service = PredictionService()
        result = service.search_communes("Lille")

        assert result == []


# ============================================================
# VIEWS — PredictionsView
# ============================================================

@pytest.mark.django_db
class TestPredictionsView:

    def test_acces_non_connecte_redirige(self, client):
        """Un utilisateur non connecté est redirigé vers le login."""
        response = client.get(reverse("predictions"))
        assert response.status_code == 302
        assert "/home" in response["Location"]

    def test_acces_connecte_200(self, authenticated_client):
        """Un utilisateur connecté accède à la page (200)."""
        response = authenticated_client.get(reverse("predictions"))
        assert response.status_code == 200

    def test_sans_code_insee_pas_de_prediction(self, authenticated_client):
        """Sans paramètre code_insee, prediction_data est None."""
        response = authenticated_client.get(reverse("predictions"))
        assert response.context["prediction_data"] is None
        assert response.context["error"] is None

    @patch("predictions.views.PredictionService.get_prediction_commune")
    def test_avec_code_insee_valide(self, mock_predict, authenticated_client, api_response_success):
        """Avec un code INSEE valide, prediction_data est rempli."""
        mock_predict.return_value = api_response_success

        response = authenticated_client.get(reverse("predictions"), {"code_insee": "59009"})

        assert response.status_code == 200
        assert response.context["prediction_data"] is not None
        assert response.context["error"] is None

    @patch("predictions.views.PredictionService.get_prediction_commune")
    def test_avec_code_insee_invalide(self, mock_predict, authenticated_client):
        """Avec un code INSEE sans résultat, error est rempli."""
        mock_predict.return_value = None

        response = authenticated_client.get(reverse("predictions"), {"code_insee": "99999"})

        assert response.status_code == 200
        assert response.context["prediction_data"] is None
        assert response.context["error"] is not None

    @patch("predictions.views.PredictionService.get_prediction_commune")
    def test_avec_code_insee_status_echec(self, mock_predict, authenticated_client):
        """Si l'API retourne un status != success, error est rempli."""
        mock_predict.return_value = {"status": "error"}

        response = authenticated_client.get(reverse("predictions"), {"code_insee": "59009"})

        assert response.context["prediction_data"] is None
        assert response.context["error"] is not None


# ============================================================
# VIEWS — commune_autocomplete
# ============================================================

@pytest.mark.django_db
class TestCommuneAutocomplete:

    def test_requete_vide_retourne_liste_vide(self, authenticated_client):
        """Si q est vide, retourne {results: []}."""
        response = authenticated_client.get(reverse("commune-search"), {"q": ""})
        assert response.status_code == 200
        assert response.json() == {"results": []}

    @patch("predictions.views.PredictionService.search_communes")
    def test_recherche_valide(self, mock_search, authenticated_client, communes_response):
        """Avec une requête valide, retourne les communes formatées."""
        mock_search.return_value = communes_response["data"]

        response = authenticated_client.get(reverse("commune-search"), {"q": "Lille"})
        data = response.json()

        assert response.status_code == 200
        assert len(data["results"]) == 2
        assert data["results"][0]["id"] == "59009"
        assert "Armentières" in data["results"][0]["text"]

    @patch("predictions.views.PredictionService.search_communes")
    def test_recherche_sans_resultat(self, mock_search, authenticated_client):
        """Si aucune commune trouvée, retourne une liste vide."""
        mock_search.return_value = []

        response = authenticated_client.get(reverse("commune-search"), {"q": "zzzzz"})
        data = response.json()

        assert response.status_code == 200
        assert data["results"] == []