"""Business request and response models."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.models.enums import CheckStatus, CheckType, Sector, Stage


class BusinessFilters(BaseModel):
    search: str | None = None
    stage: list[Stage] = []
    sector: list[Sector] = []
    score_min: int | None = None
    score_max: int | None = None
    failed_check: Literal["any", "cac", "tin", "bvn", "bank_link"] | None = None
    sort: Literal["name", "credit_score", "created_at", "last_bank_sync_at"] = "created_at"
    order: Literal["asc", "desc"] = "desc"


class _BusinessBase(BaseModel):
    id: uuid.UUID
    name: str
    cac_number: str
    sector: Sector
    state: str
    stage: Stage
    credit_score: int | None
    has_failed_check: bool
    last_bank_sync_at: datetime | None
    bank_data_stale: bool
    created_at: datetime


class BusinessListItem(_BusinessBase):
    checks: dict[CheckType, CheckStatus]


class CheckOut(BaseModel):
    type: CheckType
    status: CheckStatus
    failure_reason: str | None
    attempts: int
    updated_at: datetime


class BusinessDetail(_BusinessBase):
    tin: str
    director_name: str
    bvn_masked: str
    bank_name: str
    account_masked: str
    consent_given_at: datetime | None
    checks: list[CheckOut]
