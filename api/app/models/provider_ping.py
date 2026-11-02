"""ProviderPing ORM model."""

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._types import pg_enum
from app.models.enums import PingStatus, ProviderName


class ProviderPing(Base):
    __tablename__ = "provider_pings"
    __table_args__ = (
        sa.Index("ix_provider_pings_provider_checked_at", "provider", sa.text("checked_at DESC")),
    )

    id: Mapped[int] = mapped_column(sa.BigInteger, sa.Identity(), primary_key=True)
    provider: Mapped[ProviderName] = mapped_column(pg_enum(ProviderName, "provider"))
    status: Mapped[PingStatus] = mapped_column(pg_enum(PingStatus, "ping_status"))
    latency_ms: Mapped[int | None] = mapped_column(sa.Integer)
    error: Mapped[str | None] = mapped_column(sa.Text)
    checked_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )
