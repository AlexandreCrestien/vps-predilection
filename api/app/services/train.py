import pandas as pd
import joblib
import os
import json # <--- INDISPENSABLE
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from app.schemas.train import TrainSettings

class TrainService:
    @staticmethod
    def run_pipeline(settings: TrainSettings, db_engine):
        """ Exécute le pipeline complet de training : extraction, nettoyage, préparation, entraînement, et sauvegarde du modèle et de ses métadonnées.

        Args:
            settings (TrainSettings):  Un objet contenant les paramètres d'entraînement, notamment le nom du modèle, la taille du test, et le nombre d'estimators pour le Random Forest.
            db_engine (_type_):  L'instance de connexion à la base de données pour extraire les données d'entraînement.
        """
        try:
            # 1. Extraction
            query = "SELECT * FROM training"
            df = pd.read_sql(query, db_engine)

            if df.empty:
                print("--- ERROR: Table 'training' vide ---")
                return

            # 2. Nettoyage
            df_clean = df[
                (df['Population_active'] > 0) & 
                (df['Population avec enfants'] > 0)
            ].copy()

            # 3. Préparation X et y
            X = df_clean.drop(columns=['Code_INSEE', 'Résultat'])
            y = df_clean['Résultat']
            feature_names = list(X.columns) # On sauvegarde l'ordre ici

            # 4. Split
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=settings.test_size, random_state=42
            )

            # 5. Entraînement
            model = RandomForestClassifier(
                n_estimators=settings.n_estimators,
                random_state=42
            )
            model.fit(X_train, y_train)

            # 6. Sauvegarde du modèle (.joblib)
            os.makedirs("saved_models", exist_ok=True)
            model_path = os.path.join("saved_models", settings.model_name)
            joblib.dump(model, model_path)

            # --- GÉNÉRATION DU JSON (METADATA) ---
            
            # Calcul des importances
            importances = model.feature_importances_
            feat_imp = {name: float(imp) for name, imp in zip(feature_names, importances)}
            sorted_imp = dict(sorted(feat_imp.items(), key=lambda item: item[1], reverse=True))

            metadata = {
                "model_name": settings.model_name,
                "accuracy": float(model.score(X_test, y_test)),
                "features_order": feature_names,
                "feature_importances": sorted_imp
            }

            # Chemin du JSON
            meta_path = model_path.replace(".joblib", ".json")
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=4, ensure_ascii=False)

            print(f"--- TRAINING SUCCESS ---")
            print(f"Modèle sauvegardé : {model_path}")
            print(f"Métadonnées sauvegardées : {meta_path}")
            print(f"Précision : {metadata['accuracy']:.4f}")

        except Exception as e:
            print(f"--- TRAINING FAILED: {str(e)} ---")