"""Overview aggregates (design section 2.1 definitions). Four SQL queries in total."""

from datetime import UTC, date, datetime, timedelta, timezone

import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Business, VerificationCheck
from app.models.enums import CheckStatus, CheckType, Stage
from app.schemas.stats import (
    Cards,
    FunnelStep,
    NeedsAttention,
    OverviewStats,
    Reason,
    SignupWeek,
)
from app.services.catalog import CHECK_LABELS, STAGE_LABELS

STALE_DAYS = 7
STUCK_DAYS = 7
NEEDS_ATTENTION_LIMIT = 10
SIGNUP_WEEKS = 12
# Lagos has no daylight saving, so a fixed offset is exact and needs no tzdata package.
LAGOS = timezone(timedelta(hours=1), "Africa/Lagos")
LAGOS_TZ_NAME = "Africa/Lagos"


def _check_rollup() -> sa.Subquery:
    """One row per business summarising its checks."""
    failed = VerificationCheck.status == CheckStatus.failed
    return (
        select(
            VerificationCheck.business_id.label("business_id"),
            func.count().filter(VerificationCheck.status == CheckStatus.passed).label("passed_n"),
            func.count().filter(failed).label("failed_n"),
            func.max(VerificationCheck.updated_at).filter(failed).label("failed_at"),
            func.array_agg(sa.cast(VerificationCheck.type, sa.Text))
            .filter(failed)
            .label("failed_types"),
            func.coalesce(
                func.bool_or(
                    (VerificationCheck.type == CheckType.bank_link)
                    & (VerificationCheck.status == CheckStatus.passed)
                ),
                False,
            ).label("bank_passed"),
        )
        .group_by(VerificationCheck.business_id)
        .subquery("chk")
    )


def week_starts(now: datetime) -> list[date]:
    """The last 12 ISO weeks (Monday, Lagos time), oldest first."""
    today = now.astimezone(LAGOS).date()
    this_monday = today - timedelta(days=today.weekday())
    return [this_monday - timedelta(weeks=i) for i in range(SIGNUP_WEEKS - 1, -1, -1)]


def overview(db: Session, now: datetime | None = None) -> OverviewStats:
    now = now or datetime.now(UTC)
    stale_cutoff = now - timedelta(days=STALE_DAYS)
    stuck_cutoff = now - timedelta(days=STUCK_DAYS)
    chk = _check_rollup()

    # 1. Cards
    total, fully_verified, stuck, avg_score = db.execute(
        select(
            func.count(),
            func.count().filter(func.coalesce(chk.c.passed_n, 0) == len(CheckType)),
            func.count().filter(
                (Business.stage != Stage.profile_ready)
                & ((func.coalesce(chk.c.failed_n, 0) > 0) | (Business.created_at < stuck_cutoff))
            ),
            func.avg(Business.credit_score),
        ).select_from(Business.__table__.outerjoin(chk, chk.c.business_id == Business.id))
    ).one()

    # 2. Funnel
    counts = dict(db.execute(select(Business.stage, func.count()).group_by(Business.stage)).all())
    funnel = [FunnelStep(stage=s, label=STAGE_LABELS[s], count=counts.get(s, 0)) for s in Stage]

    # 3. Needs attention
    stale = (
        chk.c.bank_passed.is_(True)
        & Business.last_bank_sync_at.is_not(None)
        & (Business.last_bank_sync_at < stale_cutoff)
    )
    has_failed = func.coalesce(chk.c.failed_n, 0) > 0
    since = sa.case((has_failed, chk.c.failed_at), else_=Business.last_bank_sync_at)
    rows = db.execute(
        select(
            Business.id,
            Business.name,
            Business.stage,
            Business.last_bank_sync_at,
            chk.c.failed_types,
            chk.c.bank_passed,
            since.label("since"),
        )
        .select_from(Business.__table__.outerjoin(chk, chk.c.business_id == Business.id))
        .where(has_failed | stale)
        .order_by(sa.desc("since"), Business.id)
        .limit(NEEDS_ATTENTION_LIMIT)
    ).all()
    attention: list[NeedsAttention] = []
    for row in rows:
        reasons: list[Reason] = []
        failed_types = {CheckType(t) for t in (row.failed_types or [])}
        for check_type in CheckType:
            if check_type in failed_types:
                reasons.append(
                    Reason(
                        kind="failed_check",
                        check=check_type,
                        label=f"{CHECK_LABELS[check_type]} failed",
                    )
                )
        synced = row.last_bank_sync_at
        if row.bank_passed and synced is not None and synced < stale_cutoff:
            days = (now - synced).days
            reasons.append(
                Reason(kind="stale_bank_data", days=days, label=f"Bank data {days} days old")
            )
        attention.append(
            NeedsAttention(
                id=row.id, name=row.name, stage=row.stage, reasons=reasons, since=row.since
            )
        )

    # 4. Signups per Lagos week
    starts = week_starts(now)
    week = func.date_trunc("week", func.timezone(LAGOS_TZ_NAME, Business.created_at))
    first_week_start = datetime.combine(starts[0], datetime.min.time())
    signup_counts = {
        w.date(): n
        for w, n in db.execute(
            select(week, func.count()).where(week >= first_week_start).group_by(week)
        ).all()
    }
    signups = [SignupWeek(week_start=d, count=signup_counts.get(d, 0)) for d in starts]

    return OverviewStats(
        cards=Cards(
            total_businesses=total,
            fully_verified=fully_verified,
            stuck=stuck,
            avg_credit_score=None if avg_score is None else round(float(avg_score), 1),
        ),
        funnel=funnel,
        needs_attention=attention,
        signups=signups,
        generated_at=now,
    )
