import pandas as pd
import joblib
import os
import json
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException

# On récupère le chemin du dossier 'api' (2 niveaux au dessus de ce fichier service)
# predict.py -> services/ -> app/ -> api/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODELS_DIR = os.path.join(BASE_DIR, "saved_models")

class PredictionService:
    @staticmethod
    def predict_2027(db: Session, code_insee: str, model_name: str):

        """Récupère les données historiques d'une commune, projette les tendances à 2027, et utilise un modèle ML pour prédire l'orientation politique.

        Raises:
            HTTPException:  400 : Si les données historiques sont incomplètes (moins de 2 années disponibles).
            HTTPException: 500 : Si les fichiers du modèle (binaire ou JSON) sont introuvables.
            HTTPException: 500 : Si une erreur survient lors du chargement du modèle ou de la prédiction.

        Returns:
            dict: Un dictionnaire contenant la prédiction, la confiance, les scores par classe, les features les plus impactantes, et les détails des projections.
        """

        # 1. Extraction SQL : On prend TOUTES les années disponibles pour cette commune
        # On ne filtre plus sur '2011'/'2022' car cela rend le service trop rigide
        query = text("SELECT city, years, statistics FROM communes_stats WHERE code_insee = :code")
        result = db.execute(query, {"code": code_insee}).fetchall()

        if len(result) < 2:
            raise HTTPException(status_code=400, detail="Données historiques 2011/2022 incomplètes.")

        # On récupère le nom de la ville depuis la première ligne du résultat
        city_name = result[0].city if result else "Commune inconnue"

        # 2. Aplatissement et TRI (Très important pour la pente)
        data = []# On récupère le nom de la ville depuis la première ligne du résultat
        # On récupère le nom de la ville depuis la première ligne du résultat
        city_name = result[0].city if result else "Commune inconnue"

        for r in result:
            try:
                # On force la conversion de l'année en int pour un tri correct
                year_val = int(r.years)

                stats = r.statistics

                if isinstance(stats, str):
                    stats = json.loads(stats)

                data.append({"Année": year_val, **stats})
            except ValueError:
                continue # Ignore les années mal formées
        df = pd.DataFrame(data).sort_values(by="Année")

        # 3. Projection 2027 dynamique
        # On prend la plus vieille année (v1) et la plus récente (v2)
        v1_row = df.iloc[0]  # Première ligne (ex: 2011 ou 2012)
        v2_row = df.iloc[-1] # Dernière ligne (ex: 2022)

        y1 = v1_row["Année"]
        y2 = v2_row["Année"]
        delta_t = y2 - y1 # Nombre d'années entre les deux relevés
        projection_horizon = 2027 - y2 # Nombre d'années à projeter

        def project(column_name):
            if column_name in ["Année", "Résultat"]: return None
            val1 = float(v1_row[column_name])
            val2 = float(v2_row[column_name])

            # Calcul de la pente : (ValeurRécente - ValeurAncienne) / TempsÉcoulé
            pente_annuelle = (val2 - val1) / delta_t
            # Projection : ValeurRécente + (Pente * TempsRestant)
            return max(val2 + (pente_annuelle * projection_horizon), 0)

        # On applique la projection sur toutes les colonnes numériques (sauf Année/Résultat)
        cols_to_project = [c for c in df.columns if c not in ["Année", "Résultat"]]
        projections = pd.Series({c: project(c) for c in cols_to_project})

        # 4. Gestion du Zéro et calcul des Pourcentages
        pop_active = projections.get('Population_active', 0)
        pop_enfants = projections.get('Population avec enfants', 0)

        # Listes des colonnes à transformer
        labels_active = ['Hommes', 'Femmes', 'Agriculteurs', 'Artisans', 'Cadres', 'Intermédiaires', 'Employés', 'Ouvriers', 'Retraités', 'Etudiants', 'Inactifs', '15-24 ans', '25-39 ans', '40-54 ans', '55-64 ans', '65-79 ans', '80 ans et +', 'Mariés', 'Pacsés', 'Concubinage', 'Veufs', 'Divorcés', 'Célibataires']
        labels_menages = ['Personne seule', 'Homme seul', 'Femme seule', 'Colocation', 'Famille', 'Famille monoparentale', 'Couple sans enfant', 'Couple avec enfants']

        # Application sécurisée (si pop_active est 0, on met 0 au lieu de crash)
        for label in labels_active:
            projections[label] = (projections[label] / pop_active * 100) if pop_active > 0 else 0.0
        for label in labels_menages:
            projections[label] = (projections[label] / pop_enfants * 100) if pop_enfants > 0 else 0.0

        # On construit le chemin absolu

        model_path = os.path.join(MODELS_DIR, model_name)

        # On remplace .joblib par .json proprement
        meta_name = model_name.replace(".joblib", ".json")
        meta_path = os.path.join(MODELS_DIR, meta_name)

        # --- SÉCURITÉ : Vérification de l'existence des DEUX fichiers ---
        if not os.path.exists(model_path):
            raise HTTPException(status_code=500, detail=f"Modèle binaire introuvable : {model_path}")

        if not os.path.exists(meta_path):
            raise HTTPException(
                status_code=500,
                detail=f"Métadonnées JSON introuvables : {meta_path}. Relancez un entraînement."
            )

        # --- CHARGEMENT : Un avec joblib ---
        model = joblib.load(model_path)  # Chargement binaire

        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)          # Chargement texte
        # 6. Alignement et Prédiction
        # On force l'ordre des colonnes via meta["features_order"]
        X = projections.to_frame().T[meta["features_order"]]

        # On prédit la classe (ex: "Gauche", "Droite", "Centre")
        prediction_value = model.predict(X)[0]

        # On récupère les probabilités pour calculer la confiance
        proba = model.predict_proba(X)[0]

        # On convertit la confiance en pourcentage (ex: 0.85 -> 85.0%)
        confiance = round(float(max(proba)) * 100, 2)

        # Creation d'un dictionnaire des scores
        scores = {str(c): round(float(p) * 100, 2) for c, p in zip(model.classes_, proba)}

        # 7. Retour avec les features les plus impactantes
        return {
            "code_insee": code_insee,
            "city": city_name,
            "prediction_2027": str(prediction_value),
            "confiance_percent": confiance,
            "scores": scores,
            "top_features": dict(list(meta["feature_importances"].items())[:5]), # Top 5
            "details_predictions": projections.to_dict(),
            "status": "success"
        }