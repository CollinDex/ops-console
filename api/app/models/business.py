"""Business ORM model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models._types import pg_enum
from app.models.enums import Sector, Stage

if TYPE_CHECKING:
    from app.models.verification_check import VerificationCheck


class Business(Base):
    __tablename__ = "businesses"
    __table_args__ = (
        sa.CheckConstraint("bvn_last4 ~ '^[0-9]{4}$'", name="bvn_last4_digits"),
        sa.CheckConstraint("account_last4 ~ '^[0-9]{4}$'", name="account_last4_digits"),
        sa.CheckConstraint("credit_score BETWEEN 300 AND 850", name="credit_score_range"),
        sa.Index(
            "ix_businesses_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
        sa.Index(
            "ix_businesses_director_name_trgm",
            "director_name",
            postgresql_using="gin",
            postgresql_ops={"director_name": "gin_trgm_ops"},
        ),
        sa.Index("ix_businesses_stage", "stage"),
        sa.Index("ix_businesses_sector", "sector"),
        sa.Index("ix_businesses_credit_score", "credit_score"),
        sa.Index("ix_businesses_created_at", "created_at"),
        sa.Index("ix_businesses_last_bank_sync_at", "last_bank_sync_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(sa.Text)
    cac_number: Mapped[str] = mapped_column(sa.Text, unique=True)
    tin: Mapped[str] = mapped_column(sa.Text)
    sector: Mapped[Sector] = mapped_column(pg_enum(Sector, "sector"))
    state: Mapped[str] = mapped_column(sa.Text)
    director_name: Mapped[str] = mapped_column(sa.Text)
    bvn_last4: Mapped[str] = mapped_column(sa.String(4))
    bank_name: Mapped[str] = mapped_column(sa.Text)
    account_last4: Mapped[str] = mapped_column(sa.String(4))
    stage: Mapped[Stage] = mapped_column(pg_enum(Stage, "stage"))
    credit_score: Mapped[int | None] = mapped_column(sa.SmallInteger)
    consent_given_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    last_bank_sync_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()
    )

    checks: Mapped[list["VerificationCheck"]] = relationship(
        back_populates="business", lazy="selectin", order_by="VerificationCheck.type"
    )
