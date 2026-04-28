import requests
import os
from pathlib import Path

class GeoService:
    BASE_URL_LOCAL=os.environ.get("BASE_URL_LOCAL")
    BASE_URL=os.environ.get("BASE_URL")

    def get_all_departments(self):
        """ Récupère la liste de tous les départements.

        Returns:
            list: Une liste de dictionnaires contenant les informations des départements.
        """
        
        url = f"{self.BASE_URL}/departements?fields=nom,code"
        response = requests.get(url)
        return response.json() if response.status_code == 200 else []

    def get_election_results_by_department(self, department_code, year="2022"):
        """ Récupère les résultats des élections pour un département donné.

        Args:
            department_code (str): Le code du département pour lequel récupérer les résultats.

        Returns:
            dict: Un dictionnaire contenant les résultats des élections pour le département spécifié.
        """

        url = f"{self.BASE_URL_LOCAL}/communes/department/{department_code}?year={year}&limit=1000"
        try:
            response = requests.get(url)
            return response.json() if response.status_code == 200 else {}
        except Exception:
            return {}

    def get_full_map_data(self, department_code, year="2022"):
        """ Récupère les données complètes pour la carte d'un département, incluant les données géographiques et les résultats des élections.

        Args:
            department_code (str): Le code du département pour lequel récupérer les données.

        Returns:
            dict: Un dictionnaire contenant les données complètes pour la carte du département.
        """
        # 1. Données Géo
        dept_url = f"{self.BASE_URL}/departements/{department_code}?fields=nom,code,chefLieu"
        communes_url = f"{self.BASE_URL}/communes?codeDepartement={department_code}&fields=nom,code,centre,contour"
        
        dept_info = requests.get(dept_url).json()
        geo_communes = requests.get(communes_url).json()

        # 2. Données Élections (Transformation en dictionnaire pour accès rapide)
        election_resp = self.get_election_results_by_department(department_code, year=year)
        election_list = election_resp.get('data', []) if isinstance(election_resp, dict) else election_resp
        election_map = {str(item['code_insee']): item for item in election_list}

        points = []
        chef_lieu_code = dept_info.get('chefLieu')
        center_coords = [46.22, 2.21]

        for c in geo_communes:
            code = c['code']
            stats = election_map.get(code, {})
            
            if 'centre' in c:
                lat, lon = c['centre']['coordinates'][1], c['centre']['coordinates'][0]
                if code == chef_lieu_code:
                    center_coords = [lat, lon]

                points.append({
                    'nom': c['nom'],
                    'code_insee': code,
                    'lat': lat,
                    'lon': lon,
                    'contour': c.get('contour'),
                    'stats': stats
                })

        return {
            "center": center_coords,
            "communes": points,
            "dept_nom": dept_info.get('nom')
        }