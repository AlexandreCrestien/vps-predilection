from sqlalchemy import Column, Integer, Float, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class TrainingData(Base):
    __tablename__ = "training"

    # Identifiant unique (Code INSEE)
    Code_INSEE = Column(String, primary_key=True, index=True)
    Résultat = Column(String) # La cible (Label)
    
    # CSP et Genre
    Femmes = Column(Float)
    Hommes = Column(Float)
    Agriculteurs = Column(Float)
    Artisans = Column(Float)
    Cadres = Column(Float)
    Intermédiaires = Column(Float)
    Employés = Column(Float)
    Ouvriers = Column(Float)
    Retraités = Column(Float)
    Etudiants = Column(Float)
    Inactifs = Column(Float)

    # Ménages
    Personne_seule = Column(Float, name="Personne seule")
    Homme_seul = Column(Float, name="Homme seul")
    Femme_seule = Column(Float, name="Femme seule")
    Colocation = Column(Float)
    Famille = Column(Float)
    Famille_monoparentale = Column(Float, name="Famille monoparentale")
    Couple_sans_enfant = Column(Float, name="Couple sans enfant")
    Couple_avec_enfants = Column(Float, name="Couple avec enfants")
    
    # Âges
    Age_15_24 = Column(Float, name="15-24 ans")
    Age_25_39 = Column(Float, name="25-39 ans")
    Age_40_54 = Column(Float, name="40-54 ans")
    Age_55_64 = Column(Float, name="55-64 ans")
    Age_65_79 = Column(Float, name="65-79 ans")
    Age_80_plus = Column(Float, name="80 ans et +")

    # État civil
    Mariés = Column(Float)
    Pacsés = Column(Float)
    Concubinage = Column(Float)
    Veufs = Column(Float)
    Divorcés = Column(Float)
    Célibataires = Column(Float)
    
    # Bases de calcul
    Population_avec_enfants = Column(Float)
    Population_active = Column(Float)