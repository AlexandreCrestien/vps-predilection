from pydantic import BaseModel, ConfigDict

class CommuneDataSchema(BaseModel):
    Code_INSEE: str
    Résultat: str
    Femmes: float
    Hommes: float
    Agriculteurs: float
    Artisans: float
    Cadres: float
    Intermédiaires: float
    Employés: float
    Ouvriers: float
    Retraités: float
    Etudiants: float
    Inactifs: float

    # Ménages
    Personne_seule: float
    Homme_seul: float
    Femme_seule: float
    Colocation: float
    Famille: float
    Famille_monoparentale: float
    Couple_sans_enfant: float
    Couple_avec_enfants: float
    
    # Âges
    Age_15_24: float
    Age_25_39: float
    Age_40_54: float
    Age_55_64: float
    Age_65_79: float
    Age_80_plus: float

    # État civil
    Mariés: float
    Pacsés: float
    Concubinage: float
    Veufs: float
    Divorcés: float
    Célibataires: float

    # Bases de calcul
    Population_avec_enfants: float
    Population_active: float

    # Permet de transformer un objet SQLAlchemy en Pydantic automatiquement
    model_config = ConfigDict(from_attributes=True)
     

class TrainResponse(BaseModel):
    status: str
    message: str
    accuracy: float | None = None

class TrainSettings(BaseModel):
    n_estimators: int = 100
    test_size: float = 0.2
    model_name: str = "politique_model.joblib"