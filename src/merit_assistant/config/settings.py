from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_name: str = "Assistente de Avaliação de Mérito Tecnológico"
    app_log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://merit:merit@localhost:5432/merit_assistant"
    private_data_dir: Path = Path("data/private")
    max_upload_size_mb: int = Field(default=50, ge=1, le=500)
    external_processing_enabled: bool = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.private_data_dir.mkdir(parents=True, exist_ok=True)
    return settings
