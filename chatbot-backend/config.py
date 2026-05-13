from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    APP_NAME: str = "LLM Chatbot"
    DATABASE_URL: str = "sqlite:///./database.db"
    JWT_SECRET_KEY: str = "your_super_secret_key_change_this_in_production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 720
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    CORS_ORIGINS: List[str] = ["*"]

    class Config:
        env_file = ".env"

settings = Settings()
