from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.schemas.communes import PaginatedCommuneResponse
from app.db.database import get_db
from app.services.communes import CommuneService
from app.schemas.communes import CommuneResponse
from typing import List, Optional
from app.model.communes import Communes
from sqlalchemy import select, or_
from app.utils.constants import REGIONS_DEPTS

router = APIRouter(prefix="/communes", tags=["communes"])


@router.get("/", status_code=status.HTTP_200_OK, response_model=PaginatedCommuneResponse)
async def get_and_search_communes(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: str = Query(None),
    light: bool = Query(False),
    db: Session = Depends(get_db)
):
    
    """Recupère une liste paginée de communes avec possibilité de recherche et de mode léger.
    
    Args:
        skip (int): Nombre de résultats à ignorer
        limit (int): Nombre maximum de résultats à retourner
        search (str): Terme de recherche
        light (bool): Mode léger pour retourner moins de données
        
    Returns:
        List[CommuneResponse]: La liste des communes correspondantes
    """
    total, data = CommuneService.get_all(db, skip=skip, limit=limit, search=search, light=light)
    return {
        "total": total,
        "page": (skip // limit) + 1,
        "limit": limit,
        "data": data  # Pydantic filtrera automatiquement selon le mode light ou non
    }


@router.get("/commune", status_code=status.HTTP_200_OK, response_model=List[CommuneResponse])
async def get_commune_by_code(
    code_insee: str = Query(None, description="Code INSEE de la commune"),
    year: str = Query(None, description="Année des statistiques"),
    db: Session = Depends(get_db)
):
    """Récupère les communes répertoriées par le Code INSEE par année

    Args:
        code_insee (str, optional): Code INSEE de la commune.
        year (str, optional): Année des statistiques. Defaults to Query(None, description="Année des statistiques").
        db (Session, optional): Session de base de données. Defaults to Depends(get_db).

    Returns:
        List[CommuneResponse]: Liste des communes correspondantes
    """
    if code_insee and year:
        stats = CommuneService.get_by_insee(db, code_insee=code_insee, year=year)
    else:
        return status.HTTP_400_BAD_REQUEST
    return stats

@router.get("/department/{department_code}", status_code=status.HTTP_200_OK, response_model=List[CommuneResponse])
async def get_communes_by_department(
    department_code: str,
    year: Optional[str] = Query(None, description="Année des statistiques"),
    db: Session = Depends(get_db)
):
    """Récupère les communes d'un département à partir des 2 premiers caractères du code INSEE

    Args:
        department_code (str): Code du département.
        year (Optional[str], optional): Année des statistiques. Defaults to Query(None, description="Année des statistiques").
        db (Session, optional): Session de base de données. Defaults to Depends(get_db).

    Returns:
        List[CommuneResponse]: Liste des communes correspondantes
    """
    stats = CommuneService.get_by_department(db, department_code=department_code, year=year)
    return stats




@router.get("/communes/region/{region_code}")
def get_communes_by_region(region_code: str, year: str = "2022", db: Session = Depends(get_db)):
    """Récupère les communes d'une région à partir des codes des départements associés à la région.
    
    Args:
        region_code (str): Code de la région (ex: "84" pour Auvergne-Rhône-Alpes)
        year (str, optional): Année des statistiques. Default "2022".
        db (Session, optional): Session de base de données pour éviter les requêtes directes.
    Returns:
        dict: Un dictionnaire contenant le code de la région, le nombre de communes trouvées et la liste des communes.
    """
    dept_codes = REGIONS_DEPTS.get(region_code)
    if not dept_codes:
        raise HTTPException(status_code=404, detail="Région non trouvée")

    # On construit dynamiquement la clause : code_insee LIKE '01%' OR code_insee LIKE '03%' ...
    filters = [Communes.code_insee.startswith(code) for code in dept_codes]
    
    query = select(Communes).where(
        or_(*filters),
        Communes.years == year
    )
    
    result = db.execute(query).scalars().all()
    return {"region": region_code, "count": len(result), "data": result}