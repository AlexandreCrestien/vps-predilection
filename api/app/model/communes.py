from datetime import datetime
from typing import Optional, Any
from sqlalchemy import String, Float, Index, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base

class Communes(Base):
    __tablename__ = "communes_stats"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    years: Mapped[str] = mapped_column(String(4), nullable=False)
    city: Mapped[str] = mapped_column(String(255), nullable=False)
    code_insee: Mapped[str] = mapped_column(String(10), nullable=False)
    
    # Valeurs par défaut gérées au niveau du modèle
    pct_gauche: Mapped[float] = mapped_column(Float, server_default="0", default=0.0)
    pct_centre: Mapped[float] = mapped_column(Float, server_default="0", default=0.0)
    pct_droite: Mapped[float] = mapped_column(Float, server_default="0", default=0.0)
    
    # Utilisation du type JSONB spécifique à PostgreSQL
    statistics: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Timestamp automatique
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, 
        server_default=func.now(), 
        onupdate=func.now()
    )

    __table_args__ = (
        # Contrainte d'unicité (years, code_insee)
        UniqueConstraint("years", "code_insee", name="unique_city_year"),
        # Index GIN pour les requêtes JSON performantes
        Index("idx_communes_stats_stats_gin", "statistics", postgresql_using="gin"),
    )