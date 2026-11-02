"""Audit log writing."""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.staff_user import StaffUser
from app.schemas.audit import AuditActor, AuditEntry


def write_audit(
    db: Session,
    *,
    actor_id: uuid.UUID | None,
    action: str,
    target_type: str,
    target_id: str | None,
    details: dict[str, Any],
) -> None:
    """Add an audit row. Does not commit: the caller owns the transaction."""
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details,
        )
    )


def list_for_business(db: Session, business_id: uuid.UUID, limit: int = 50) -> list[AuditEntry]:
    """Newest first. System rows (no actor) come back with actor=None."""
    rows = db.execute(
        select(AuditLog, StaffUser)
        .outerjoin(StaffUser, AuditLog.actor_id == StaffUser.id)
        .where(AuditLog.target_type == "business", AuditLog.target_id == str(business_id))
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(limit)
    ).all()
    return [
        AuditEntry(
            id=log.id,
            action=log.action,
            actor=(
                AuditActor(id=user.id, full_name=user.full_name, role=user.role) if user else None
            ),
            details=log.details,
            created_at=log.created_at,
        )
        for log, user in rows
    ]
