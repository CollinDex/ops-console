"""Stats router: overview numbers for the dashboard. Open to every role."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models import StaffUser
from app.schemas.stats import OverviewStats
from app.services import stats as stats_service

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/overview", response_model=OverviewStats)
def overview(
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[StaffUser, Depends(get_current_user)],
) -> OverviewStats:
    return stats_service.overview(db)
