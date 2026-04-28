import requests
import os

class PredictionService:
    BASE_URL_LOCAL=os.environ.get("BASE_URL_LOCAL")

    def get_prediction_commune(self, code_insee):
        """ Récupère les prédictions pour une commune donnée.

        Args:
            code_insee (str): Le code INSEE de la commune pour laquelle récupérer les prédictions.

        Returns:
            dict: Un dictionnaire contenant les prédictions pour la commune spécifiée.
        """
        url = f"{self.BASE_URL_LOCAL}/predict/2027/{code_insee}"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Erreur API: {e}")
            return None
        
    def search_communes(self, query):
        """ Recherche des communes en fonction d'une requête de recherche.

        Args:
            query (str): La requête de recherche.

        Returns:
            list: Une liste de dictionnaires contenant les informations des communes trouvées.
        """
        # Ajout du / après communes et vérification de la construction de l'URL
        url = f"{self.BASE_URL_LOCAL}/communes/?search={query}&limit=50&light=true"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                # Ton service renvoie déjà le contenu de ['data']
                return response.json().get('data', [])
            return []
        except Exception as e:
            print(f"Erreur API: {e}")
            return []