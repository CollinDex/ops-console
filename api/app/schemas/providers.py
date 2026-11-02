"""Provider status, incident and simulate schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.models.enums import ProviderName


class PingPointOut(BaseModel):
    checked_at: datetime
    status: Literal["up", "slow", "down"]
    latency_ms: int | None


class ProviderStatusOut(BaseModel):
    name: ProviderName
    label: str
    # "unknown" exists only here (no pings yet), not in the DB enum.
    status: Literal["up", "slow", "down", "unknown"]
    mode: Literal["up", "slow", "down"]
    latency_ms: int | None
    last_checked_at: datetime | None
    uptime_24h: float | None
    avg_latency_24h: int | None
    recent: list[PingPointOut]


class ProviderSummary(BaseModel):
    up: int
    slow: int
    down: int


class ProvidersStatusOut(BaseModel):
    providers: list[ProviderStatusOut]
    summary: ProviderSummary
    generated_at: datetime


class IncidentOut(BaseModel):
    started_at: datetime
    ended_at: datetime | None
    duration_seconds: int
    worst_status: Literal["down", "slow"]
    ping_count: int


class SimulateIn(BaseModel):
    mode: Literal["up", "slow", "down"]
