"""Application settings, read from environment variables."""

import json
from functools import lru_cache
from typing import Annotated, Any, Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

DEV_JWT_SECRET = "dev-only-change-me"  # noqa: S105


def normalise_database_url(url: str) -> str:
    """Hosts hand out postgres:// or postgresql:// URLs. SQLAlchemy needs the psycopg 3 driver."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://credisure:credisure@localhost:5433/credisure"
    test_database_url: str = (
        "postgresql+psycopg://credisure:credisure@localhost:5433/credisure_test"
    )
    jwt_secret: str = DEV_JWT_SECRET
    jwt_ttl_minutes: int = 60
    bcrypt_rounds: int = 12
    # Accepts a JSON list or a comma-separated string (what hosting dashboards usually take).
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]
    env: Literal["local", "test", "prod"] = "local"
    pinger_enabled: bool = True
    app_version: str = "0.1.0"

    @field_validator("database_url", "test_database_url")
    @classmethod
    def _normalise_db_url(cls, value: str) -> str:
        return normalise_database_url(value)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: Any) -> Any:
        if isinstance(value, str):
            text = value.strip()
            if text.startswith("["):
                return json.loads(text)
            return [o.strip().rstrip("/") for o in text.split(",") if o.strip()]
        return value

    @model_validator(mode="after")
    def _require_real_secret_in_prod(self) -> "Settings":
        if self.env == "prod" and self.jwt_secret == DEV_JWT_SECRET:
            raise ValueError("JWT_SECRET must be set when ENV=prod")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
