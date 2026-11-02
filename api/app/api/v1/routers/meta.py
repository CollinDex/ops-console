"""Meta router: filter options for the UI."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.security import require_roles
from app.models import StaffUser
from app.models.enums import CheckType, Role, Sector, Stage
from app.schemas.meta import FilterMeta, Option, ScoreBandOut
from app.services.catalog import CHECK_LABELS, SCORE_BANDS, SECTOR_LABELS, STAGE_LABELS

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/filters", response_model=FilterMeta)
def filters(
    _user: Annotated[
        StaffUser,
        Depends(require_roles(Role.analyst, Role.ops_admin, action="view filter options")),
    ],
) -> FilterMeta:
    return FilterMeta(
        stages=[Option(value=s.value, label=STAGE_LABELS[s]) for s in Stage],
        sectors=[
            Option(value=s.value, label=SECTOR_LABELS[s])
            for s in sorted(Sector, key=lambda s: SECTOR_LABELS[s])
        ],
        check_types=[Option(value=t.value, label=CHECK_LABELS[t]) for t in CheckType],
        score_bands=[ScoreBandOut(**band) for band in SCORE_BANDS],
    )
