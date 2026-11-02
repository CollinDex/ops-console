"""Business query building and row shaping, shared by the list, detail and CSV export."""

import csv
import io
import uuid
from collections.abc import Iterable, Iterator, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import Select, and_, exists, func, or_, select
from sqlalchemy.orm import Session, lazyload

from app.api.deps import like_escape
from app.models import Business, VerificationCheck
from app.models.enums import CheckStatus, CheckType
from app.schemas.business import (
    BusinessDetail,
    BusinessFilters,
    BusinessListItem,
    CheckOut,
)
from app.services.masking import mask_account, mask_bvn

STALE_DAYS = 7
EXPORT_ROW_CAP = 10_000
EXPORT_COLUMNS = [
    "name",
    "cac_number",
    "sector",
    "state",
    "stage",
    "credit_score",
    "cac",
    "tin",
    "bvn",
    "bank_link",
    "last_bank_sync_at",
    "joined",
]

# Allow-list: the request value is only ever a key here, never interpolated into SQL.
_SORT_COLUMNS = {
    "name": Business.name,
    "credit_score": Business.credit_score,
    "created_at": Business.created_at,
    "last_bank_sync_at": Business.last_bank_sync_at,
}
_NULLABLE_SORTS = {"credit_score", "last_bank_sync_at"}


def build_business_query(filters: BusinessFilters) -> Select[Business]:
    """The single query behind both the list and the CSV export."""
    query = select(Business).options(lazyload(Business.checks))

    if filters.search:
        escaped = like_escape(filters.search)
        query = query.where(
            or_(
                Business.name.ilike(f"%{escaped}%", escape="\\"),
                Business.director_name.ilike(f"%{escaped}%", escape="\\"),
                Business.cac_number.ilike(f"{escaped.upper()}%", escape="\\"),
            )
        )
    if filters.stage:
        query = query.where(Business.stage.in_(filters.stage))
    if filters.sector:
        query = query.where(Business.sector.in_(filters.sector))
    if filters.score_min is not None:
        query = query.where(Business.credit_score >= filters.score_min)
    if filters.score_max is not None:
        query = query.where(Business.credit_score <= filters.score_max)
    if filters.failed_check is not None:
        conditions = [
            VerificationCheck.business_id == Business.id,
            VerificationCheck.status == CheckStatus.failed,
        ]
        if filters.failed_check != "any":
            conditions.append(VerificationCheck.type == CheckType(filters.failed_check))
        query = query.where(exists().where(and_(*conditions)))

    column = _SORT_COLUMNS[filters.sort]
    ordered = column.asc() if filters.order == "asc" else column.desc()
    if filters.sort in _NULLABLE_SORTS:
        ordered = ordered.nulls_last()
    return query.order_by(ordered, Business.id)


def count_businesses(db: Session, query: Select[Business]) -> int:
    return db.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0


def load_check_statuses(
    db: Session, business_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, dict[CheckType, CheckStatus]]:
    """One batched query for the check statuses of many businesses."""
    result: dict[uuid.UUID, dict[CheckType, CheckStatus]] = {bid: {} for bid in business_ids}
    if not business_ids:
        return result
    rows = db.execute(
        select(
            VerificationCheck.business_id, VerificationCheck.type, VerificationCheck.status
        ).where(VerificationCheck.business_id.in_(business_ids))
    )
    for business_id, check_type, status in rows:
        result[business_id][check_type] = status
    return result


def _ordered(statuses: dict[CheckType, CheckStatus]) -> dict[CheckType, CheckStatus]:
    return {t: statuses[t] for t in CheckType if t in statuses}


def is_bank_data_stale(
    bank_link_status: CheckStatus | None, last_sync: datetime | None, now: datetime
) -> bool:
    return (
        bank_link_status == CheckStatus.passed
        and last_sync is not None
        and last_sync < now - timedelta(days=STALE_DAYS)
    )


def to_list_items(
    businesses: Iterable[Business],
    statuses: dict[uuid.UUID, dict[CheckType, CheckStatus]],
    now: datetime | None = None,
) -> list[BusinessListItem]:
    now = now or datetime.now(UTC)
    items = []
    for b in businesses:
        checks = _ordered(statuses.get(b.id, {}))
        items.append(
            BusinessListItem(
                id=b.id,
                name=b.name,
                cac_number=b.cac_number,
                sector=b.sector,
                state=b.state,
                stage=b.stage,
                credit_score=b.credit_score,
                checks=checks,
                has_failed_check=CheckStatus.failed in checks.values(),
                last_bank_sync_at=b.last_bank_sync_at,
                bank_data_stale=is_bank_data_stale(
                    checks.get(CheckType.bank_link), b.last_bank_sync_at, now
                ),
                created_at=b.created_at,
            )
        )
    return items


def to_detail(business: Business, now: datetime | None = None) -> BusinessDetail:
    now = now or datetime.now(UTC)
    order = {t: i for i, t in enumerate(CheckType)}
    checks = sorted(business.checks, key=lambda c: order[c.type])
    by_type = {c.type: c.status for c in checks}
    return BusinessDetail(
        id=business.id,
        name=business.name,
        cac_number=business.cac_number,
        sector=business.sector,
        state=business.state,
        stage=business.stage,
        credit_score=business.credit_score,
        has_failed_check=CheckStatus.failed in by_type.values(),
        last_bank_sync_at=business.last_bank_sync_at,
        bank_data_stale=is_bank_data_stale(
            by_type.get(CheckType.bank_link), business.last_bank_sync_at, now
        ),
        created_at=business.created_at,
        tin=business.tin,
        director_name=business.director_name,
        bvn_masked=mask_bvn(business.bvn_last4),
        bank_name=business.bank_name,
        account_masked=mask_account(business.account_last4),
        consent_given_at=business.consent_given_at,
        checks=[
            CheckOut(
                type=c.type,
                status=c.status,
                failure_reason=c.failure_reason,
                attempts=c.attempts,
                updated_at=c.updated_at,
            )
            for c in checks
        ],
    )


def _csv_safe(value: str) -> str:
    """Stop spreadsheet apps from running a cell as a formula."""
    return "'" + value if value[:1] in ("=", "+", "-", "@", "\t", "\r") else value


def _iso(value: datetime | None) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ") if value else ""


def csv_rows(
    businesses: Sequence[Business],
    statuses: dict[uuid.UUID, dict[CheckType, CheckStatus]],
) -> Iterator[str]:
    """Yield the CSV one line at a time. No director name or identifiers (data minimisation)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    def flush() -> str:
        line = buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)
        return line

    writer.writerow(EXPORT_COLUMNS)
    yield flush()
    for b in businesses:
        checks = statuses.get(b.id, {})
        row: list[Any] = [
            _csv_safe(b.name),
            b.cac_number,
            b.sector.value,
            b.state,
            b.stage.value,
            "" if b.credit_score is None else b.credit_score,
            *(checks[t].value if t in checks else "" for t in CheckType),
            _iso(b.last_bank_sync_at),
            _iso(b.created_at),
        ]
        writer.writerow(row)
        yield flush()


def audit_filters(filters: BusinessFilters) -> dict[str, Any]:
    """The non-empty filters, JSON-safe, for the export audit row."""
    data = filters.model_dump(mode="json", exclude={"sort", "order"})
    return {k: v for k, v in data.items() if v not in (None, [], "")}
