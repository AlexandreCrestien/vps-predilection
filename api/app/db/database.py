from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from typing import Generator
from app.core.config import settings

# L'engine est la source de connectivité
engine = create_engine(settings.DATABASE_URL)

# SessionLocal est une classe qui créera des instances de session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base est la classe de base pour les modèles SQLAlchemy
Base = declarative_base()

# Dépendance pour FastAPI (Dependency Injection)
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()