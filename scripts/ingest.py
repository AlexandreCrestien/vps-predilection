import os
import sys
import pandas as pd
import numpy as np
import json
import time
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# --- CONFIGURATION DES CHEMINS (IMPORTANT) ---
# 1. On trouve la racine du projet (political-prediction/)
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# 2. On pointe vers le .env qui est dans le dossier 'api'
dotenv_path = os.path.join(root_path, 'api', '.env')

# 3. Chargement manuel du .env AVANT d'importer les settings
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    print(f"✅ .env chargé depuis : {dotenv_path}")
else:
    print(f"❌ Erreur : .env introuvable à {dotenv_path}")
    sys.exit(1)

# 4. On ajoute le dossier 'api' au sys.path pour que 'from app...' fonctionne
sys.path.append(os.path.join(root_path, 'api'))

from app.core.config import settings

def convert_columns_to_percentages(df, list_columns, divider_column):
    df_conv = df.copy()
    mask = df_conv[divider_column] > 0
    df_conv.loc[mask, list_columns] = df_conv.loc[mask, list_columns].div(df_conv[divider_column], axis=0) * 100
    df_conv[list_columns] = df_conv[list_columns].fillna(0).replace([np.inf, -np.inf], 0)
    return df_conv

def run_ingestion():
    print(f"🔗 Connexion à la base : {settings.DATABASE_URL}")
    engine = create_engine(settings.DATABASE_URL)
    
    # 1. Attente / Vérification de la DB
    for i in range(5):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                print("✅ Connexion réussie à Postgres.")
                break
        except Exception:
            print(f"⏳ Tentative de connexion... ({i+1}/5)")
            time.sleep(2)

    # 2. Chargement du CSV
    csv_path = os.path.join(root_path, 'data', 'df_stats.csv')
    if not os.path.exists(csv_path):
        print(f"❌ Fichier CSV introuvable à : {csv_path}")
        return
        
    df_raw = pd.read_csv(csv_path, sep=';', dtype={'Code_INSEE': str})

    # --- PARTIE 1 : TRAINING ---
    print("📦 Préparation table 'training'...")
    df_train = df_raw[df_raw['Année'] == 2022].copy()
    
    cols_active = ['Hommes', 'Femmes', 'Agriculteurs', 'Artisans', 'Cadres', 'Intermédiaires', 'Employés', 'Ouvriers', 'Retraités', 'Etudiants', 'Inactifs', '15-24 ans', '25-39 ans', '40-54 ans', '55-64 ans', '65-79 ans', '80 ans et +', 'Mariés', 'Pacsés', 'Concubinage', 'Veufs', 'Divorcés', 'Célibataires']
    df_train = convert_columns_to_percentages(df_train, cols_active, 'Population_active')
    
    cols_household = ['Personne seule', 'Homme seul', 'Femme seule', 'Colocation', 'Famille', 'Famille monoparentale', 'Couple sans enfant', 'Couple avec enfants']
    df_train = convert_columns_to_percentages(df_train, cols_household, 'Population avec enfants')

    training_cols = ['Code_INSEE', 'Résultat', 'Femmes', 'Hommes', 'Agriculteurs', 'Artisans', 'Cadres', 'Intermédiaires', 'Employés', 'Ouvriers', 'Retraités', 'Etudiants', 'Inactifs', 'Personne seule', 'Homme seul', 'Femme seule', 'Colocation', 'Famille', 'Famille monoparentale', 'Couple sans enfant', 'Couple avec enfants', '15-24 ans', '25-39 ans', '40-54 ans', '55-64 ans', '65-79 ans', '80 ans et +', 'Mariés', 'Pacsés', 'Concubinage', 'Veufs', 'Divorcés', 'Célibataires', 'Population avec enfants', 'Population_active']
    
    df_train[training_cols].to_sql('training', engine, if_exists='replace', index=False)
    print("✅ Table 'training' injectée.")

    # --- PARTIE 2 : COMMUNES_STATS ---
    print("📦 Préparation table 'communes_stats'...")
    df_communes = df_raw.copy()

    
    cols_json = [
        'Inscrits', 'Abstentions', 'Votants', 'Blancs', 'Nuls', 'Exprimés', 'Résultat',
        'Population avec enfants', 'Population_active'
    ] + cols_active + cols_household
    
    df_final = pd.DataFrame({
        'years': df_communes['Année'].astype(str),
        'city': df_communes['Libellé de la commune'].fillna("Inconnu"),
        'code_insee': df_communes['Code_INSEE'].astype(str),
        'pct_gauche': pd.to_numeric(df_communes['% gauche/Exp'], errors='coerce').fillna(0),
        'pct_centre': pd.to_numeric(df_communes['% centre/Exp'], errors='coerce').fillna(0),
        'pct_droite': pd.to_numeric(df_communes['% droite/Exp'], errors='coerce').fillna(0),
        'statistics': df_communes[cols_json].fillna(0).to_dict(orient='records')
    })
    df_final['statistics'] = df_final['statistics'].apply(json.dumps)

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS communes_stats (
                id SERIAL PRIMARY KEY,
                years VARCHAR(4) NOT NULL,
                city VARCHAR(255) NOT NULL,
                code_insee VARCHAR(10) NOT NULL,
                pct_gauche FLOAT DEFAULT 0,
                pct_centre FLOAT DEFAULT 0,
                pct_droite FLOAT DEFAULT 0,
                statistics JSONB,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT unique_city_year UNIQUE (years, code_insee)
            );
        """))

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE communes_stats;"))

    # 2. On insère les données avec 'append' au lieu de 'replace'
    df_final.to_sql('communes_stats', engine, if_exists='append', index=False, method='multi', chunksize=500)
    print("✅ Table 'communes_stats' injectée avec succès !")

if __name__ == "__main__":
    run_ingestion()
