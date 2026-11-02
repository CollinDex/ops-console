"""Staff router: the team list."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import PaginationDep, clean_search, like_escape
from app.core.security import require_roles
from app.db.session import get_db
from app.models import StaffUser
from app.models.enums import Role
from app.schemas.common import Page
from app.schemas.staff import StaffOut

router = APIRouter(prefix="/staff", tags=["staff"])

_SORT_COLUMNS = {
    "full_name": StaffUser.full_name,
    "created_at": StaffUser.created_at,
    "role": StaffUser.role,
}


@router.get("", response_model=Page[StaffOut])
def list_staff(
    pagination: PaginationDep,
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[
        StaffUser,
        Depends(require_roles(Role.analyst, Role.ops_admin, action="view the team")),
    ],
    search: Annotated[str | None, Query()] = None,
    role: Annotated[list[Role] | None, Query()] = None,
    sort: Annotated[Literal["full_name", "created_at", "role"], Query()] = "full_name",
    order: Annotated[Literal["asc", "desc"], Query()] = "asc",
) -> Page[StaffOut]:
    query = select(StaffUser)
    term = clean_search(search)
    if term:
        pattern = f"%{like_escape(term)}%"
        query = query.where(
            or_(
                StaffUser.full_name.ilike(pattern, escape="\\"),
                StaffUser.email.ilike(pattern, escape="\\"),
            )
        )
    if role:
        query = query.where(StaffUser.role.in_(role))
    column = _SORT_COLUMNS[sort]
    query = query.order_by(column.asc() if order == "asc" else column.desc(), StaffUser.id)
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    rows = db.scalars(query.limit(pagination.page_size).offset(pagination.offset)).all()
    return Page(
        items=[StaffOut.model_validate(r) for r in rows],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )
