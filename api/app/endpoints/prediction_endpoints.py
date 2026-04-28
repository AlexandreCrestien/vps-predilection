from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.services.predict import PredictionService
from app.schemas.predict import PredictionResponse

router = APIRouter(prefix="/predict", tags=["prediction"])

@router.get("/2027/{code_insee}", response_model=PredictionResponse)
async def predict_2027(code_insee: str, db: Session = Depends(get_db)):
    """Prédit les résultat des élection présidentielle d'une commune

    Args:
        code_insee (str): Code INSEE de la commune
        db (Session, optional): Session de base de données. 

    Returns:
        PredictionResponse: Les résultats de la prédiction
    """

    return PredictionService.predict_2027(db, code_insee, "politique_model.joblib")