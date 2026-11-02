"""Overview stats response models."""

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

from app.models.enums import CheckType, Stage


class Cards(BaseModel):
    total_businesses: int
    fully_verified: int
    stuck: int
    avg_credit_score: float | None


class FunnelStep(BaseModel):
    stage: Stage
    label: str
    count: int


class Reason(BaseModel):
    kind: Literal["failed_check", "stale_bank_data"]
    check: CheckType | None = None
    days: int | None = None
    label: str


class NeedsAttention(BaseModel):
    id: uuid.UUID
    name: str
    stage: Stage
    reasons: list[Reason]
    since: datetime


class SignupWeek(BaseModel):
    week_start: date
    count: int


class OverviewStats(BaseModel):
    cards: Cards
    funnel: list[FunnelStep]
    needs_attention: list[NeedsAttention]
    signups: list[SignupWeek]
    generated_at: datetime
