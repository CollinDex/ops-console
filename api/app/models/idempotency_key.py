"""IdempotencyKey ORM model."""

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    key: Mapped[str] = mapped_column(sa.String(128), primary_key=True)
    actor_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("staff_users.id"), primary_key=True)
    request_hash: Mapped[str] = mapped_column(sa.String(64))
    response_status: Mapped[int | None] = mapped_column(sa.SmallInteger)
    response: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )
