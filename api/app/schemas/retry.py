"""Retry response schema (design section 6.4)."""

from pydantic import BaseModel

from app.models.enums import Stage
from app.schemas.business import CheckOut


class RetryOut(BaseModel):
    check: CheckOut
    business_stage: Stage
    replayed: bool
