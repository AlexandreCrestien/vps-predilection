from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import List, Optional, Any, Union

# Schéma léger pour l'autocomplétion
class CommuneLight(BaseModel):
    code_insee: str
    city: str
    model_config = ConfigDict(from_attributes=True)

class CommuneResponse(BaseModel):
    id: int
    years: str = Field(..., max_length=4)
    city: str
    code_insee: str
    pct_gauche: float
    pct_centre: float
    pct_droite: float
    statistics: Optional[dict[str, Any]] = None
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class PaginatedCommuneResponse(BaseModel):
    total: int
    page: int
    limit: int
    # Union permet d'accepter soit la liste complète, soit la liste légère
    data: List[Union[CommuneResponse, CommuneLight]]