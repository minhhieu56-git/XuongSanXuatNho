from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://workshop:workshop@localhost:5432/workshop"
    jwt_secret: str = "development-only-change-me"
    access_token_expire_minutes: int = 60
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    frontend_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]


settings = Settings()
