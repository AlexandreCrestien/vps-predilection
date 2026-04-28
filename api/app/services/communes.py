from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_
from app.model.communes import Communes

class CommuneService:
    @staticmethod
    def get_by_insee(db: Session, code_insee: str, year: str = None):
        """Récupère une commune par son code INSEE, avec un filtre optionnel sur l'année.

        Args:
            db (Session): _description_
            code_insee (str): Le code INSEE de la commune à rechercher.
            year (str, optional): L'année pour laquelle on souhaite filtrer les données. Si None, toutes les années sont incluses. Defaults to None.

        Returns:
            List[Communes]: La liste des communes correspondantes au code INSEE (et à l'année si spécifiée).
        """
        query = select(Communes).where(Communes.code_insee == code_insee)
        if year:
            query = query.where(Communes.years == year)
        
        result = db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100, search: str = None, light: bool = False):
        """Récupère toute la liste des communes, avec pagination, recherche et option de sélection légère.
        Args:
            db (Session): _description_
            skip (int, optional): représente le nombre d'éléments à ignorer avant de commencer à retourner les résultats (pour la pagination). Defaults to 0.
            limit (int, optional): représente le nombre maximum d'éléments à retourner (pour la pagination). Defaults to 100.
            search (str, optional): Le terme de recherche pour filtrer les communes. Defaults to None.
            light (bool, optional): Indique si l'on souhaite un mode léger (retourne moins de données). Defaults to False.

        Returns:
            Tuple[int, List[Communes] | List[Dict]]: Un tuple contenant le nombre total de communes correspondant à la recherche et la liste des communes (soit en mode complet, soit en mode léger).
        """
        
        if light:
            # On sélectionne uniquement les deux colonnes
            data_query = select(Communes.code_insee, Communes.city).distinct()
        else:
            data_query = select(Communes)

        total_query = select(func.count()).select_from(Communes)

        if search and search.strip():
            filter_stmt = or_(
                Communes.city.ilike(f"%{search}%"),
                Communes.code_insee.ilike(f"{search}%")
            )
            total_query = total_query.where(filter_stmt)
            data_query = data_query.where(filter_stmt)

        total = db.execute(total_query).scalar() or 0
        data_query = data_query.offset(skip).limit(limit)
        
        result = db.execute(data_query)
        
        if light:
            # mappings().all() transforme les lignes en dictionnaires {'code_insee': ..., 'city': ...}
            return total, result.mappings().all()
        
        return total, result.scalars().all()
    
    @staticmethod
    def get_by_department(db: Session, department_code: str, year: str = None, light: bool = False):
        """Récupère les données des communes d'un département donné, avec un filtre optionnel sur l'année et une option de sélection légère.

        Args:
            db (Session): _session de la base de données pour exécuter les requêtes.
            department_code (str): Le code du département pour lequel on souhaite récupérer les communes (ex: '59' pour le Nord).
            year (str, optional): L'année pour laquelle on souhaite filtrer les données. Si None, toutes les années sont incluses. Defaults to None.
            light (bool, optional): Indique si l'on souhaite un mode léger (retourne moins de données). Defaults to False.

        Returns:
            List[Communes] | List[Dict]: La liste des communes du département correspondant au code (et à l'année si spécifiée). Le format de retour dépend du mode léger ou complet.
        """
        
        if light:
            # Mode Carte : Sélection restreinte pour alléger les données
            query = select(
                Communes.code_insee, 
                Communes.city, 
                Communes.pct_gauche, 
                Communes.pct_centre,
                Communes.pct_droite,
                Communes.years
            )
        else:
            # Mode Tableau : Object complet (Toutes les colonnes + JSON)
            query = select(Communes)
        # Filtres communes
        query = select(Communes).where(Communes.code_insee.startswith(department_code))
        if year:
            query = query.where(Communes.years == year)

        result = db.execute(query)

        if light:
            # Pour la sélection de colonnes, on renvoie des dictionnaires
            return [dict(row) for row in result.mappings().all()]
        # Pour l'objet complet, on renvoie les instances du modèle
        return result.scalars().all()
    
    
    @staticmethod
    def get_by_region(db: Session, department_codes: list[str], year: str = "2022"):
        """
        Récupère toutes les communes pour une liste de départements (une région).
        
        Args:
            db (Session): _description_
            department_codes (list[str]): Liste des codes de départements à inclure dans la recherche (ex: ['59', '62'] pour les Hauts-de-France).
            year (str, optional): L'année pour laquelle on souhaite filtrer les données. Si None, toutes les années sont incluses. Defaults to "2022".
            
        Returns:
            List[Communes]: La liste des communes correspondant aux départements spécifiés (et à l'année si spécifiée).
        """
        # Construction d'une clause OR pour chaque département
        filters = [Communes.code_insee.startswith(code) for code in department_codes]
        
        query = select(Communes).where(or_(*filters))
        if year:
            query = query.where(Communes.years == year)
            
        result = db.execute(query)
        return result.scalars().all()