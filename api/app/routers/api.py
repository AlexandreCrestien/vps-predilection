from fastapi import APIRouter
from app.endpoints.prediction_endpoints import router as prediction_router
from app.endpoints.model_endpoints import router as model_router
from app.endpoints.communes_endpoints import router as commune_router
from app.endpoints.train_endpoints import router as train_router
from app.endpoints.prediction_endpoints import router as prediction_router

api_router = APIRouter()
api_router.include_router(prediction_router)
api_router.include_router(model_router)
api_router.include_router(commune_router) 
api_router.include_router(train_router)
api_router.include_router(prediction_router)
