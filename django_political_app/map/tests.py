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
def departments_response():
    return [
        {"nom": "Nord", "code": "59"},
        {"nom": "Pas-de-Calais", "code": "62"},
    ]


@pytest.fixture
def election_response():
    return {
        "data": [
            {
                "code_insee": "59009",
                "pct_gauche": 40.0,
                "pct_centre": 30.0,
                "pct_droite": 30.0,
                "statistics": {"pct_abstention": 25.0},
            },
            {
                "code_insee": "59350",
                "pct_gauche": 20.0,
                "pct_centre": 50.0,
                "pct_droite": 30.0,
                "statistics": {"pct_abstention": 30.0},
            },
        ]
    }


@pytest.fixture
def full_map_data():
    return {
        "center": [50.6, 3.06],
        "dept_nom": "Nord",
        "communes": [
            {
                "nom": "Armentières",
                "code_insee": "59009",
                "lat": 50.68,
                "lon": 2.88,
                "contour": None,
                "stats": {
                    "pct_gauche": 40.0,
                    "pct_centre": 30.0,
                    "pct_droite": 30.0,
                },
            }
        ],
    }


# ============================================================
# SERVICES — GeoService
# ============================================================

class TestGeoService:

    @patch("map.services.requests.get")
    def test_get_all_departments_succes(self, mock_get, departments_response):
        """Retourne la liste des départements si l'API répond 200."""
        from map.services import GeoService
        mock_get.return_value = MagicMock(status_code=200, json=lambda: departments_response)

        service = GeoService()
        result = service.get_all_departments()

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["code"] == "59"

    @patch("map.services.requests.get")
    def test_get_all_departments_erreur(self, mock_get):
        """Retourne une liste vide si l'API répond autre chose que 200."""
        from map.services import GeoService
        mock_get.return_value = MagicMock(status_code=500)

        service = GeoService()
        result = service.get_all_departments()

        assert result == []

    @patch("map.services.requests.get")
    def test_get_election_results_succes(self, mock_get, election_response):
        """Retourne les résultats électoraux si l'API répond 200."""
        from map.services import GeoService
        mock_get.return_value = MagicMock(status_code=200, json=lambda: election_response)

        service = GeoService()
        result = service.get_election_results_by_department("59", year="2022")

        assert isinstance(result, dict)
        assert "data" in result
        assert len(result["data"]) == 2

    @patch("map.services.requests.get")
    def test_get_election_results_erreur(self, mock_get):
        """Retourne un dict vide si l'API répond autre chose que 200."""
        from map.services import GeoService
        mock_get.return_value = MagicMock(status_code=404)

        service = GeoService()
        result = service.get_election_results_by_department("59")

        assert result == {}

    @patch("map.services.requests.get")
    def test_get_election_results_exception(self, mock_get):
        """Retourne un dict vide si une exception est levée."""
        from map.services import GeoService
        mock_get.side_effect = Exception("Timeout")

        service = GeoService()
        result = service.get_election_results_by_department("59")

        assert result == {}

    @patch.object(__import__("map.services", fromlist=["GeoService"]).GeoService, "get_election_results_by_department")
    @patch("map.services.requests.get")
    def test_get_full_map_data_structure(self, mock_get, mock_election, election_response):
        """Retourne un dict avec center, communes et dept_nom."""
        from map.services import GeoService

        dept_info = {"nom": "Nord", "code": "59", "chefLieu": "59350"}
        geo_communes = [
            {
                "nom": "Armentières",
                "code": "59009",
                "centre": {"coordinates": [2.88, 50.68]},
                "contour": None,
            }
        ]

        mock_get.side_effect = [
            MagicMock(status_code=200, json=lambda: dept_info),
            MagicMock(status_code=200, json=lambda: geo_communes),
        ]
        mock_election.return_value = election_response

        service = GeoService()
        result = service.get_full_map_data("59", year="2022")

        assert "center" in result
        assert "communes" in result
        assert "dept_nom" in result
        assert result["dept_nom"] == "Nord"
        assert isinstance(result["communes"], list)


# ============================================================
# VIEWS — get_city_color
# ============================================================

class TestGetCityColor:

    def setup_method(self):
        from map.views import MapView
        self.view = MapView()

    def test_couleur_gauche(self):
        stats = {"pct_gauche": 50, "pct_centre": 20, "pct_droite": 30}
        assert self.view.get_city_color(stats) == "#e74c3c"

    def test_couleur_centre(self):
        stats = {"pct_gauche": 20, "pct_centre": 50, "pct_droite": 30}
        assert self.view.get_city_color(stats) == "#f1c40f"

    def test_couleur_droite(self):
        stats = {"pct_gauche": 20, "pct_centre": 20, "pct_droite": 60}
        assert self.view.get_city_color(stats) == "#3498db"

    def test_couleur_egalite(self):
        stats = {"pct_gauche": 33, "pct_centre": 33, "pct_droite": 33}
        assert self.view.get_city_color(stats) == "#95a5a6"

    def test_couleur_sans_donnees(self):
        assert self.view.get_city_color({}) == "#bdc3c7"

    def test_couleur_stats_none(self):
        assert self.view.get_city_color(None) == "#bdc3c7"


# ============================================================
# VIEWS — MapView
# ============================================================

@pytest.mark.django_db
class TestMapView:

    def test_acces_non_connecte_redirige(self, client):
        """Un utilisateur non connecté est redirigé vers le login."""
        response = client.get(reverse("map"))
        assert response.status_code == 302
        assert "/home" in response["Location"]

    @patch("map.views.GeoService.get_all_departments")
    @patch("map.views.GeoService.get_full_map_data")
    def test_acces_connecte_200(self, mock_map, mock_depts, authenticated_client, full_map_data, departments_response):
        """Un utilisateur connecté accède à la page (200)."""
        mock_map.return_value = full_map_data
        mock_depts.return_value = departments_response

        response = authenticated_client.get(reverse("map"))
        assert response.status_code == 200

    @patch("map.views.GeoService.get_all_departments")
    @patch("map.views.GeoService.get_full_map_data")
    def test_departement_par_defaut_59(self, mock_map, mock_depts, authenticated_client, full_map_data, departments_response):
        """Sans paramètre, le département par défaut est 59."""
        mock_map.return_value = full_map_data
        mock_depts.return_value = departments_response

        response = authenticated_client.get(reverse("map"))
        assert response.context["current_dept"] == "59"

    @patch("map.views.GeoService.get_all_departments")
    @patch("map.views.GeoService.get_full_map_data")
    def test_annee_par_defaut_2022(self, mock_map, mock_depts, authenticated_client, full_map_data, departments_response):
        """Sans paramètre year, l'année par défaut est 2022."""
        mock_map.return_value = full_map_data
        mock_depts.return_value = departments_response

        response = authenticated_client.get(reverse("map"))
        assert response.context["current_year"] == "2022"

    @patch("map.views.GeoService.get_all_departments")
    @patch("map.views.GeoService.get_full_map_data")
    def test_changement_departement(self, mock_map, mock_depts, authenticated_client, full_map_data, departments_response):
        """Le paramètre department est bien transmis au contexte."""
        mock_map.return_value = full_map_data
        mock_depts.return_value = departments_response

        response = authenticated_client.get(reverse("map"), {"department": "62"})
        assert response.context["current_dept"] == "62"

    @patch("map.views.GeoService.get_all_departments")
    @patch("map.views.GeoService.get_full_map_data")
    def test_changement_annee(self, mock_map, mock_depts, authenticated_client, full_map_data, departments_response):
        """Le paramètre year est bien transmis au contexte."""
        mock_map.return_value = full_map_data
        mock_depts.return_value = departments_response

        response = authenticated_client.get(reverse("map"), {"year": "2017"})
        assert response.context["current_year"] == "2017"

    @patch("map.views.GeoService.get_all_departments")
    @patch("map.views.GeoService.get_full_map_data")
    def test_contexte_contient_departments(self, mock_map, mock_depts, authenticated_client, full_map_data, departments_response):
        """Le contexte contient bien la liste des départements."""
        mock_map.return_value = full_map_data
        mock_depts.return_value = departments_response

        response = authenticated_client.get(reverse("map"))
        assert "departments" in response.context
        assert len(response.context["departments"]) == 2