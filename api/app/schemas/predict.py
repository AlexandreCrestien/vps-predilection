from pydantic import BaseModel
from typing import Dict, Any, Optional


class PredictionResponse(BaseModel):
    code_insee: str
    prediction_2027: str
    confiance_percent: float
    city: str
    # Les 5 variables qui ont le plus influencé le modèle
    scores: Dict[str, float]
    top_features: Dict[str, float]
    # Les données brutes projetées pour vérification
    details_predictions: Dict[str, float]
    status: str = "success"