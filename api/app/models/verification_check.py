"""VerificationCheck ORM model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models._types import pg_enum
from app.models.enums import CheckStatus, CheckType

if TYPE_CHECKING:
    from app.models.business import Business


class VerificationCheck(Base):
    __tablename__ = "verification_checks"
    __table_args__ = (
        sa.UniqueConstraint("business_id", "type", name="uq_verification_checks_business_id_type"),
        sa.CheckConstraint("attempts >= 0", name="attempts_non_negative"),
        sa.Index(
            "ix_verification_checks_failed",
            "type",
            postgresql_where=sa.text("status = 'failed'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("businesses.id", ondelete="CASCADE")
    )
    type: Mapped[CheckType] = mapped_column(pg_enum(CheckType, "check_type"))
    status: Mapped[CheckStatus] = mapped_column(
        pg_enum(CheckStatus, "check_status"), server_default=CheckStatus.pending.value
    )
    failure_reason: Mapped[str | None] = mapped_column(sa.Text)
    attempts: Mapped[int] = mapped_column(sa.Integer, default=0, server_default=sa.text("0"))
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()
    )

    business: Mapped["Business"] = relationship(back_populates="checks")
