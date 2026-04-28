import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime

# ============================================================
# SETUP CLIENT
# ============================================================

# On doit setter DATABASE_URL avant d'importer l'app
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from app.main import app

client = TestClient(app)


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def commune_data():
    return {
        "id": 1,
        "years": "2022",
        "city": "Armentières",
        "code_insee": "59009",
        "pct_gauche": 40.0,
        "pct_centre": 30.0,
        "pct_droite": 30.0,
        "statistics": {"pct_abstention": 25.0},
        "updated_at": datetime(2022, 1, 1).isoformat(),
    }


@pytest.fixture
def commune_light_data():
    return {"code_insee": "59009", "city": "Armentières"}


@pytest.fixture
def prediction_data():
    return {
        "code_insee": "59009",
        "prediction_2027": "Gauche",
        "confiance_percent": 85.0,
        "scores": {"Gauche": 85.0, "Centre": 10.0, "Droite": 5.0},
        "top_features": {"Ouvriers": 0.12, "Retraités": 0.10},
        "details_predictions": {"Ouvriers": 35.0},
        "status": "success",
    }


# ============================================================
# ENDPOINT ROOT
# ============================================================

class TestRoot:

    def test_root_retourne_200(self):
        response = client.get("/")
        assert response.status_code == 200

    def test_root_retourne_hello_world(self):
        response = client.get("/")
        assert response.json() == {"message": "Hello World"}


# ============================================================
# ENDPOINT COMMUNES — GET /communes/
# ============================================================

class TestGetCommunes:

    @patch("app.endpoints.communes_endpoints.CommuneService.get_all")
    def test_get_communes_200(self, mock_service, commune_data):
        mock_service.return_value = (1, [MagicMock(**commune_data)])
        response = client.get("/communes/")
        assert response.status_code == 200

    @patch("app.endpoints.communes_endpoints.CommuneService.get_all")
    def test_get_communes_structure_reponse(self, mock_service, commune_data):
        """La réponse contient total, page, limit et data."""
        mock_service.return_value = (1, [MagicMock(**commune_data)])
        response = client.get("/communes/")
        data = response.json()
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        assert "data" in data

    @patch("app.endpoints.communes_endpoints.CommuneService.get_all")
    def test_get_communes_pagination_defaut(self, mock_service, commune_data):
        """Sans paramètres, skip=0 et limit=50 par défaut."""
        mock_service.return_value = (1, [MagicMock(**commune_data)])
        client.get("/communes/")
        mock_service.assert_called_once()
        _, kwargs = mock_service.call_args
        assert kwargs["skip"] == 0
        assert kwargs["limit"] == 50

    @patch("app.endpoints.communes_endpoints.CommuneService.get_all")
    def test_get_communes_avec_recherche(self, mock_service, commune_data):
        """Le paramètre search est bien transmis au service."""
        mock_service.return_value = (1, [MagicMock(**commune_data)])
        client.get("/communes/?search=Lille")
        _, kwargs = mock_service.call_args
        assert kwargs["search"] == "Lille"

    @patch("app.endpoints.communes_endpoints.CommuneService.get_all")
    def test_get_communes_mode_light(self, mock_service, commune_light_data):
        """Le paramètre light=true est bien transmis au service."""
        mock_service.return_value = (1, [commune_light_data])
        client.get("/communes/?light=true")
        _, kwargs = mock_service.call_args
        assert kwargs["light"] is True

    def test_get_communes_limit_invalide(self):
        """limit > 100 retourne 422 (validation Pydantic)."""
        response = client.get("/communes/?limit=200")
        assert response.status_code == 422

    def test_get_communes_skip_negatif(self):
        """skip < 0 retourne 422 (validation Pydantic)."""
        response = client.get("/communes/?skip=-1")
        assert response.status_code == 422


# ============================================================
# ENDPOINT COMMUNES — GET /communes/commune
# ============================================================

class TestGetCommuneByCode:

    @patch("app.endpoints.communes_endpoints.CommuneService.get_by_insee")
    def test_get_commune_par_code_200(self, mock_service, commune_data):
        mock_service.return_value = [MagicMock(**commune_data)]
        response = client.get("/communes/commune?code_insee=59009&year=2022")
        assert response.status_code == 200

    @patch("app.endpoints.communes_endpoints.CommuneService.get_by_insee")
    def test_get_commune_transmet_code_et_annee(self, mock_service, commune_data):
        mock_service.return_value = [MagicMock(**commune_data)]
        client.get("/communes/commune?code_insee=59009&year=2022")
        mock_service.assert_called_once()
        _, kwargs = mock_service.call_args
        assert kwargs["code_insee"] == "59009"
        assert kwargs["year"] == "2022"


# ============================================================
# ENDPOINT COMMUNES — GET /communes/department/{code}
# ============================================================

class TestGetCommunesByDepartment:

    @patch("app.endpoints.communes_endpoints.CommuneService.get_by_department")
    def test_get_communes_departement_200(self, mock_service, commune_data):
        mock_service.return_value = [MagicMock(**commune_data)]
        response = client.get("/communes/department/59")
        assert response.status_code == 200

    @patch("app.endpoints.communes_endpoints.CommuneService.get_by_department")
    def test_get_communes_departement_avec_annee(self, mock_service, commune_data):
        mock_service.return_value = [MagicMock(**commune_data)]
        client.get("/communes/department/59?year=2022")
        _, kwargs = mock_service.call_args
        assert kwargs["year"] == "2022"

    @patch("app.endpoints.communes_endpoints.CommuneService.get_by_department")
    def test_get_communes_departement_liste_vide(self, mock_service):
        mock_service.return_value = []
        response = client.get("/communes/department/99")
        assert response.status_code == 200
        assert response.json() == []


# ============================================================
# ENDPOINT COMMUNES — GET /communes/communes/region/{code}
# ============================================================

class TestGetCommunesByRegion:

    @patch("app.endpoints.communes_endpoints.CommuneService")
    def test_region_inconnue_retourne_404(self, mock_service):
        """Un code région inexistant retourne 404."""
        response = client.get("/communes/communes/region/99")
        assert response.status_code == 404


# ============================================================
# ENDPOINT PREDICTION — GET /predict/2027/{code_insee}
# ============================================================

class TestPredictionEndpoint:

    @patch("app.endpoints.prediction_endpoints.PredictionService.predict_2027")
    def test_predict_2027_200(self, mock_predict, prediction_data):
        mock_predict.return_value = prediction_data
        response = client.get("/predict/2027/59009")
        assert response.status_code == 200

    @patch("app.endpoints.prediction_endpoints.PredictionService.predict_2027")
    def test_predict_2027_structure_reponse(self, mock_predict, prediction_data):
        """La réponse contient tous les champs attendus."""
        mock_predict.return_value = prediction_data
        response = client.get("/predict/2027/59009")
        data = response.json()
        assert "code_insee" in data
        assert "prediction_2027" in data
        assert "confiance_percent" in data
        assert "scores" in data
        assert "status" in data

    @patch("app.endpoints.prediction_endpoints.PredictionService.predict_2027")
    def test_predict_2027_transmet_code_insee(self, mock_predict, prediction_data):
        """Le code INSEE est bien transmis au service."""
        mock_predict.return_value = prediction_data
        client.get("/predict/2027/59009")
        args, _ = mock_predict.call_args
        assert args[1] == "59009"

    @patch("app.endpoints.prediction_endpoints.PredictionService.predict_2027")
    def test_predict_2027_donnees_incompletes_400(self, mock_predict):
        """Si les données historiques sont incomplètes, retourne 400."""
        from fastapi import HTTPException
        mock_predict.side_effect = HTTPException(
            status_code=400,
            detail="Données historiques 2011/2022 incomplètes."
        )
        response = client.get("/predict/2027/00000")
        assert response.status_code == 400

    @patch("app.endpoints.prediction_endpoints.PredictionService.predict_2027")
    def test_predict_2027_modele_introuvable_500(self, mock_predict):
        """Si le modèle est introuvable, retourne 500."""
        from fastapi import HTTPException
        mock_predict.side_effect = HTTPException(
            status_code=500,
            detail="Modèle binaire introuvable."
        )
        response = client.get("/predict/2027/59009")
        assert response.status_code == 500


# ============================================================
# ENDPOINT TRAIN — POST /train/
# ============================================================

class TestTrainEndpoint:

    def test_train_lance_en_arriere_plan_202(self):
        """POST /train/ retourne 202 et lance la tâche en arrière-plan."""
        payload = {
            "n_estimators": 100,
            "test_size": 0.2,
            "model_name": "test_model.joblib"
        }
        response = client.post("/train/", json=payload)
        assert response.status_code == 202

    def test_train_reponse_contient_status_processing(self):
        """La réponse contient status=processing."""
        payload = {
            "n_estimators": 100,
            "test_size": 0.2,
            "model_name": "test_model.joblib"
        }
        response = client.post("/train/", json=payload)
        assert response.json()["status"] == "processing"

    def test_train_reponse_contient_settings(self):
        """La réponse inclut les settings envoyés."""
        payload = {
            "n_estimators": 50,
            "test_size": 0.3,
            "model_name": "mon_modele.joblib"
        }
        response = client.post("/train/", json=payload)
        data = response.json()
        assert data["settings"]["model_name"] == "mon_modele.joblib"
        assert data["settings"]["n_estimators"] == 50

    def test_train_valeurs_par_defaut(self):
        """Sans paramètres, les valeurs par défaut sont utilisées."""
        response = client.post("/train/", json={})
        assert response.status_code == 202
        data = response.json()
        assert data["settings"]["n_estimators"] == 100
        assert data["settings"]["model_name"] == "politique_model.joblib"

    def test_train_body_manquant(self):
        """Sans body, retourne 422."""
        response = client.post("/train/")
        assert response.status_code == 422


# ============================================================
# ENDPOINT MODEL — GET /model/ et POST /model/
# ============================================================

class TestModelEndpoint:

    def test_get_model_200(self):
        response = client.get("/model/")
        assert response.status_code == 200

    def test_post_model_201(self):
        response = client.post("/model/")
        assert response.status_code == 201