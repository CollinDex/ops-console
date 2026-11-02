from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Business, StaffUser, VerificationCheck
from app.models.enums import CheckStatus, CheckType, Stage
from app.services.stage import derive_stage
from scripts.seed import run_seed

NOW = datetime(2026, 11, 3, 9, 0, tzinfo=UTC)

pytestmark = pytest.mark.slow


def test_seed_counts_and_consistency(db: Session) -> None:
    summary = run_seed(db, now=NOW)
    assert db.scalar(select(func.count()).select_from(Business)) == 300
    assert db.scalar(select(func.count()).select_from(VerificationCheck)) == 1200
    assert db.scalar(select(func.count()).select_from(StaffUser)) == 15
    stages = set(db.scalars(select(Business.stage)))
    assert stages == set(Stage)
    assert summary.stale_bank >= 20

    stale = db.scalar(
        select(func.count())
        .select_from(Business)
        .join(VerificationCheck)
        .where(
            VerificationCheck.type == CheckType.bank_link,
            VerificationCheck.status == CheckStatus.passed,
            Business.last_bank_sync_at < NOW - timedelta(days=7),
        )
    )
    assert stale == summary.stale_bank

    for b in db.scalars(select(Business)):
        assert len(b.checks) == 4
        statuses = {c.type: c.status for c in b.checks}
        if b.stage in (Stage.signed_up, Stage.documents_submitted):
            assert b.credit_score is None
            assert set(statuses.values()) == {CheckStatus.pending}
        else:
            assert b.credit_score is not None and 300 <= b.credit_score <= 850
            assert derive_stage(b.stage, statuses, b.consent_given_at) == b.stage


def test_seed_is_deterministic(db: Session) -> None:
    run_seed(db, now=NOW)
    first = list(
        db.execute(select(Business.name, Business.cac_number).order_by(Business.cac_number))
    )
    run_seed(db, now=NOW, reset=True)
    second = list(
        db.execute(select(Business.name, Business.cac_number).order_by(Business.cac_number))
    )
    assert first == second
    assert len(first) == 300


def test_seed_pings_and_retry_audit(db: Session) -> None:
    from app.models import AuditLog, ProviderPing
    from app.models.enums import ProviderName
    from app.services.providers import PingPoint, group_incidents

    summary = run_seed(db, now=NOW)
    assert summary.pings == 4 * 7 * 24 * 60
    assert db.scalar(select(func.count()).select_from(ProviderPing)) == summary.pings
    counts = {}
    for name in ProviderName:
        rows = db.execute(
            select(ProviderPing.checked_at, ProviderPing.status)
            .where(ProviderPing.provider == name)
            .order_by(ProviderPing.checked_at)
        ).all()
        counts[name] = group_incidents([PingPoint(r.checked_at, r.status) for r in rows], NOW)
    assert [(i.worst_status, i.duration_seconds) for i in counts[ProviderName.bvn]] == [
        ("down", 25 * 60)
    ]
    assert [(i.worst_status, i.duration_seconds) for i in counts[ProviderName.open_banking]] == [
        ("slow", 120 * 60)
    ]
    assert [(i.worst_status, i.duration_seconds) for i in counts[ProviderName.cac]] == [
        ("down", 10 * 60)
    ]
    assert len(counts[ProviderName.tin]) == 2
    assert summary.retry_audit == 12
    retries = db.scalars(select(AuditLog).where(AuditLog.action == "check.retry")).all()
    assert len(retries) == 12 and all(r.actor_id for r in retries)
