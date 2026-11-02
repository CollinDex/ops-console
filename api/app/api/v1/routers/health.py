"""Health router: application and database status."""

import logging
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.services.providers import ping_summary

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)


@router.get("/health")
def health(db: Annotated[Session, Depends(get_db)]) -> JSONResponse:
    body: dict[str, Any] = {
        "status": "ok",
        "db": "ok",
        "providers": {"up": 0, "slow": 0, "down": 0},
        "version": get_settings().app_version,
        "time": datetime.now(UTC).isoformat(),
    }
    try:
        db.execute(text("SELECT 1"))
        summary = ping_summary(db)
    except Exception:
        logger.exception("health check: database unreachable")
        body["status"] = "down"
        body["db"] = "down"
        return JSONResponse(status_code=503, content=body)
    body["providers"] = summary.model_dump()
    if summary.slow or summary.down:
        body["status"] = "degraded"
    return JSONResponse(content=body)
