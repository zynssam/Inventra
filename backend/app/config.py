"""
app/config.py — loads settings from environment variables.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./stocksense.db"
    SECRET_KEY: str = "change-me"
    DEBUG: bool = False
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours
    ALGORITHM: str = "HS256"
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
