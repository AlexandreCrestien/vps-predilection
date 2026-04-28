from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    
    # Charge le fichier .env automatiquement
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()