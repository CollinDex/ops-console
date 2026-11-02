"""Idempotent check retry (design section 7.3, ADR-004).

Runs in a worker thread (sync route). The provider call is async, so it hops to the event
loop with anyio.from_thread.run. The key row is committed before that call, and no DB
transaction is open while the provider is being called.
"""

import asyncio
import hashlib
import logging
import re
import uuid
from datetime import UTC, datetime
from typing import Any

import anyio.from_thread
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import (
    CheckNotRetryable,
    IdempotencyKeyReused,
    NotFound,
    RequestInProgress,
)
from app.models import Business, IdempotencyKey, StaffUser, VerificationCheck
from app.models.enums import CheckStatus, CheckType
from app.providers.base import CALL_TIMEOUT_S, CheckResult, ProviderUnavailable
from app.providers.registry import ProviderRegistry
from app.providers.simulator import SimulatedProvider
from app.schemas.business import CheckOut
from app.schemas.retry import RetryOut
from app.services.audit import write_audit
from app.services.stage import derive_stage

logger = logging.getLogger(__name__)

KEY_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,128}$")


def key_is_valid(key: str) -> bool:
    return KEY_PATTERN.fullmatch(key) is not None


def request_hash(business_id: uuid.UUID, check_type: CheckType, actor_id: uuid.UUID) -> str:
    raw = f"POST|/businesses/{business_id}/checks/{check_type.value}/retry|{actor_id}"
    return hashlib.sha256(raw.encode()).hexdigest()


async def _verify_with_timeout(
    provider: SimulatedProvider, business_id: uuid.UUID, check_type: CheckType
) -> CheckResult:
    return await asyncio.wait_for(provider.verify(business_id, check_type), CALL_TIMEOUT_S)


def _release_key(db: Session, key: str, actor_id: uuid.UUID) -> None:
    db.rollback()
    db.execute(
        delete(IdempotencyKey).where(IdempotencyKey.key == key, IdempotencyKey.actor_id == actor_id)
    )
    db.commit()


def _claim_key(db: Session, key: str, actor_id: uuid.UUID, req_hash: str) -> RetryOut | None:
    """Insert and commit the key. Returns a stored response if this is a replay."""
    db.add(IdempotencyKey(key=key, actor_id=actor_id, request_hash=req_hash))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalars(
            select(IdempotencyKey).where(
                IdempotencyKey.key == key, IdempotencyKey.actor_id == actor_id
            )
        ).one_or_none()
        if existing is None:  # deleted between our insert and select: treat as still in flight
            raise RequestInProgress() from None
        if existing.request_hash != req_hash:
            raise IdempotencyKeyReused() from None
        if existing.response is None:
            raise RequestInProgress() from None
        body: dict[str, Any] = {**existing.response, "replayed": True}
        return RetryOut.model_validate(body)
    return None


def retry_check(
    db: Session,
    registry: ProviderRegistry,
    *,
    business_id: uuid.UUID,
    check_type: CheckType,
    key: str,
    actor: StaffUser,
) -> RetryOut:
    """Run the algorithm of design 7.3. `RetryOut.replayed` tells the router about replays."""
    actor_id = actor.id
    if db.get(Business, business_id) is None:
        raise NotFound("Business not found.")

    replay = _claim_key(db, key, actor_id, request_hash(business_id, check_type, actor_id))
    if replay is not None:
        return replay

    # From here on the key is ours: any early exit that is not a stored outcome must free it.
    check = db.scalars(
        select(VerificationCheck).where(
            VerificationCheck.business_id == business_id, VerificationCheck.type == check_type
        )
    ).one_or_none()
    if check is None or check.status != CheckStatus.failed:
        _release_key(db, key, actor_id)
        raise CheckNotRetryable()
    db.commit()  # end the read transaction: no DB transaction is open during the provider call

    provider = registry.for_check(check_type)
    try:
        result = anyio.from_thread.run(_verify_with_timeout, provider, business_id, check_type)
    except (ProviderUnavailable, TimeoutError):
        result = CheckResult(False, f"Provider unavailable ({provider.name.value})")
    except BaseException:
        logger.exception("provider call failed unexpectedly")
        _release_key(db, key, actor_id)
        raise

    try:
        return _commit_outcome(db, business_id, check_type, key, actor_id, result)
    except BaseException:
        _release_key(db, key, actor_id)
        raise


def _commit_outcome(
    db: Session,
    business_id: uuid.UUID,
    check_type: CheckType,
    key: str,
    actor_id: uuid.UUID,
    result: CheckResult,
) -> RetryOut:
    now = datetime.now(UTC)
    business = db.scalars(
        select(Business).where(Business.id == business_id).execution_options(populate_existing=True)
    ).one()
    check = next(c for c in business.checks if c.type == check_type)
    check.status = CheckStatus.passed if result.passed else CheckStatus.failed
    check.failure_reason = None if result.passed else result.failure_reason
    check.attempts += 1
    check.updated_at = now
    business.stage = derive_stage(
        business.stage, {c.type: c.status for c in business.checks}, business.consent_given_at
    )
    if check_type == CheckType.bank_link and result.passed:
        business.last_bank_sync_at = now
    business.updated_at = now
    write_audit(
        db,
        actor_id=actor_id,
        action="check.retry",
        target_type="business",
        target_id=str(business_id),
        details={
            "check": check_type.value,
            "result": "passed" if result.passed else "failed",
            "failure_reason": check.failure_reason,
            "attempts": check.attempts,
            "idempotency_key": key,
        },
    )
    out = RetryOut(
        check=CheckOut.model_validate(check, from_attributes=True),
        business_stage=business.stage,
        replayed=False,
    )
    stored = db.get(IdempotencyKey, (key, actor_id))
    assert stored is not None  # noqa: S101 - we own this row
    stored.response_status = 200
    stored.response = out.model_dump(mode="json")
    db.commit()
    return out
