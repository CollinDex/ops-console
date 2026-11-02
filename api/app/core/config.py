"""Application settings, read from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://credisure:credisure@localhost:5433/credisure"
    test_database_url: str = (
        "postgresql+psycopg://credisure:credisure@localhost:5433/credisure_test"
    )
    jwt_secret: str = "dev-only-change-me"  # noqa: S105
    jwt_ttl_minutes: int = 60
    cors_origins: list[str] = ["http://localhost:3000"]
    env: Literal["local", "test", "prod"] = "local"
    pinger_enabled: bool = True
    app_version: str = "0.1.0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
