"""Audit timeline schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.enums import Role


class AuditActor(BaseModel):
    id: uuid.UUID
    full_name: str
    role: Role


class AuditEntry(BaseModel):
    id: int
    action: str
    actor: AuditActor | None
    details: dict[str, Any]
    created_at: datetime
