"""Health response schema (documents GET /health in OpenAPI)."""

from typing import Literal

from pydantic import BaseModel


class HealthProviders(BaseModel):
    up: int
    slow: int
    down: int


class HealthOut(BaseModel):
    status: Literal["ok", "degraded", "down"]
    db: Literal["ok", "down"]
    providers: HealthProviders
    version: str
    time: str
