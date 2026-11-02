"""Businesses router: list, CSV export, detail, audit timeline and idempotent check retry."""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import PaginationDep, clean_search
from app.core.errors import IdempotencyKeyRequired, NotFound, ValidationFailed
from app.core.security import require_roles
from app.db.session import get_db
from app.models import Business, StaffUser
from app.models.enums import CheckType, Role, Sector, Stage
from app.providers.registry import ProviderRegistry, get_registry
from app.schemas.audit import AuditEntry
from app.schemas.business import BusinessDetail, BusinessFilters, BusinessListItem
from app.schemas.common import Page
from app.schemas.retry import RetryOut
from app.services import businesses as svc
from app.services import retry as retry_svc
from app.services.audit import list_for_business, write_audit

router = APIRouter(prefix="/businesses", tags=["businesses"])

_ROLES = (Role.analyst, Role.ops_admin)
DbDep = Annotated[Session, Depends(get_db)]


def get_filters(
    search: Annotated[str | None, Query()] = None,
    stage: Annotated[list[Stage] | None, Query()] = None,
    sector: Annotated[list[Sector] | None, Query()] = None,
    score_min: Annotated[int | None, Query(ge=300, le=850)] = None,
    score_max: Annotated[int | None, Query(ge=300, le=850)] = None,
    failed_check: Annotated[str | None, Query(pattern="^(any|cac|tin|bvn|bank_link)$")] = None,
    sort: Annotated[str, Query(pattern="^(name|credit_score|created_at|last_bank_sync_at)$")] = (
        "created_at"
    ),
    order: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
) -> BusinessFilters:
    if score_min is not None and score_max is not None and score_min > score_max:
        raise ValidationFailed(
            "The request is invalid.",
            details=[{"field": "score_min", "message": "score_min must not exceed score_max."}],
        )
    return BusinessFilters.model_validate(
        {
            "search": clean_search(search),
            "stage": stage or [],
            "sector": sector or [],
            "score_min": score_min,
            "score_max": score_max,
            "failed_check": failed_check,
            "sort": sort,
            "order": order,
        }
    )


FiltersDep = Annotated[BusinessFilters, Depends(get_filters)]


def _parse_id(business_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(business_id)
    except ValueError as exc:
        raise NotFound("Business not found.") from exc


@router.get("", response_model=Page[BusinessListItem])
def list_businesses(
    filters: FiltersDep,
    pagination: PaginationDep,
    db: DbDep,
    _user: Annotated[StaffUser, Depends(require_roles(*_ROLES, action="view businesses"))],
) -> Page[BusinessListItem]:
    query = svc.build_business_query(filters)
    total = svc.count_businesses(db, query)
    rows = db.scalars(query.limit(pagination.page_size).offset(pagination.offset)).all()
    statuses = svc.load_check_statuses(db, [b.id for b in rows])
    return Page(
        items=svc.to_list_items(rows, statuses),
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


# Declared before "/{business_id}" so "export.csv" is not parsed as an id.
@router.get("/export.csv", response_class=StreamingResponse)
def export_csv(
    filters: FiltersDep,
    db: DbDep,
    user: Annotated[StaffUser, Depends(require_roles(*_ROLES, action="export businesses"))],
) -> StreamingResponse:
    cap = svc.EXPORT_ROW_CAP
    rows = list(db.scalars(svc.build_business_query(filters).limit(cap + 1)).all())
    truncated = len(rows) > cap
    rows = rows[:cap]
    statuses = svc.load_check_statuses(db, [b.id for b in rows])
    write_audit(
        db,
        actor_id=user.id,
        action="businesses.export",
        target_type="business",
        target_id=None,
        details={"filters": svc.audit_filters(filters), "rows": len(rows)},
    )
    db.commit()
    filename = f"credisure-businesses-{datetime.now(UTC):%Y%m%d}.csv"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    if truncated:
        headers["X-Truncated"] = "true"
    return StreamingResponse(
        svc.csv_rows(rows, statuses), media_type="text/csv; charset=utf-8", headers=headers
    )


@router.get("/{business_id}", response_model=BusinessDetail)
def get_business(
    business_id: str,
    db: DbDep,
    _user: Annotated[StaffUser, Depends(require_roles(*_ROLES, action="view business details"))],
) -> BusinessDetail:
    business = db.get(Business, _parse_id(business_id))
    if business is None:
        raise NotFound("Business not found.")
    return svc.to_detail(business)


@router.get("/{business_id}/audit", response_model=list[AuditEntry])
def business_audit(
    business_id: str,
    db: DbDep,
    _user: Annotated[StaffUser, Depends(require_roles(*_ROLES, action="view the audit log"))],
) -> list[AuditEntry]:
    parsed = _parse_id(business_id)
    if db.get(Business, parsed) is None:
        raise NotFound("Business not found.")
    return list_for_business(db, parsed)


# Sync on purpose: runs in a worker thread so the sync session never blocks the event loop.
@router.post("/{business_id}/checks/{check_type}/retry", response_model=RetryOut)
def retry_check(
    business_id: str,
    check_type: str,
    response: Response,
    db: DbDep,
    registry: Annotated[ProviderRegistry, Depends(get_registry)],
    user: Annotated[StaffUser, Depends(require_roles(Role.ops_admin, action="re-run checks"))],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> RetryOut:
    key = (idempotency_key or "").strip()
    if not key:
        raise IdempotencyKeyRequired()
    if not retry_svc.key_is_valid(key):
        raise ValidationFailed(
            "The request is invalid.",
            details=[
                {
                    "field": "header.Idempotency-Key",
                    "message": "Must be 8-128 characters: letters, digits, '-' or '_'.",
                }
            ],
        )
    parsed = _parse_id(business_id)
    try:
        parsed_type = CheckType(check_type)
    except ValueError as exc:
        raise NotFound("Unknown check type.") from exc
    result = retry_svc.retry_check(
        db, registry, business_id=parsed, check_type=parsed_type, key=key, actor=user
    )
    if result.replayed:
        response.headers["Idempotent-Replayed"] = "true"
    return result
