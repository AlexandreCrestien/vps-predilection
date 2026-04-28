import requests
import os
from pathlib import Path

class DetailService:
    BASE_URL_LOCAL = os.environ.get("BASE_URL_LOCAL")
    def get_detail_communes(self, page=1, limit=25, search=None):
        
        """ Récupère les détails des communes avec pagination et recherche.

        Args:
            page (int, optional): Numéro de la page. Defaults to 1.
            limit (int, optional): Nombre d'éléments par page. Defaults to 25.
            search (str, optional): Terme de recherche pour filtrer les communes. Defaults to None.
            
        Returns:
            dict: Un dictionnaire contenant les détails des communes, le nombre total, la page actuelle et la limite.
        """
        
        limit = min(int(limit), 100)  # Limite à 100 pour éviter les requêtes trop lourdes
        skip = (page - 1) * limit
        url = f"{self.BASE_URL_LOCAL}/communes/?skip={skip}&limit={limit}"
        params = {
            "skip": skip,
            "limit": limit
        }
        
        if search:
            params["search"] = search

        try:
            reponse = requests.get(url, params=params)
            if reponse.status_code == 200:
                return reponse.json()
        except Exception as e:
            print(f"Erreur lors de la récupération des détails des communes : {e}")
        return {"total": 0, "page": page, "limit": limit, "data": []}