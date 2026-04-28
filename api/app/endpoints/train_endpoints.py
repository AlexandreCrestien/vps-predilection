from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.engine import Engine
from app.db.database import engine  # On importe l'engine directement
from app.schemas.train import TrainSettings
from app.services.train import TrainService

router = APIRouter(prefix="/train", tags=["train"])

@router.post("/", status_code=status.HTTP_202_ACCEPTED)
async def launch_model_training(
    settings: TrainSettings, 
    background_tasks: BackgroundTasks
):
    """Lance le service d'entraînement du modèle

    Args:
        settings (TrainSettings): Paramètres d'entraînement du modèle
        background_tasks (BackgroundTasks): Tâches en arrière-plan

    Returns:
        dict: Statut de la tâche
    """
    # On délègue la tâche au service en arrière-plan
    background_tasks.add_task(TrainService.run_pipeline, settings, engine)
    
    return {
        "status": "processing",
        "message": f"L'entraînement du modèle '{settings.model_name}' a été lancé en arrière-plan.",
        "settings": settings
    }