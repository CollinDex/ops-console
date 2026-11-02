"""AuditLog ORM model."""

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        sa.Index("ix_audit_log_target", "target_type", "target_id", sa.text("created_at DESC")),
    )

    id: Mapped[int] = mapped_column(sa.BigInteger, sa.Identity(), primary_key=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(sa.ForeignKey("staff_users.id"))
    action: Mapped[str] = mapped_column(sa.Text)
    target_type: Mapped[str] = mapped_column(sa.Text)
    target_id: Mapped[str | None] = mapped_column(sa.Text)
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default=sa.text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )
