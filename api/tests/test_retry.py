import asyncio
import threading
import uuid
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import SessionLocal, engine, get_session_factory
from app.main import create_app
from app.models import AuditLog, Business, IdempotencyKey, StaffUser
from app.models.enums import CheckStatus, CheckType, ProviderName, Role, Stage
from app.providers.base import CheckResult
from app.providers.registry import ProviderRegistry, get_registry
from app.providers.simulator import SimulatedProvider
from tests.conftest import make_registry
from tests.factories import make_business

FAILED_BVN = {
    CheckType.cac: CheckStatus.passed,
    CheckType.tin: CheckStatus.passed,
    CheckType.bvn: CheckStatus.failed,
    CheckType.bank_link: CheckStatus.passed,
}


def _url(business: Business, check: str = "bvn") -> str:
    return f"/api/v1/businesses/{business.id}/checks/{check}/retry"


def _key() -> str:
    return str(uuid.uuid4())


def _post(client: TestClient, business: Business, headers: dict[str, str], key: str | None) -> Any:
    h = dict(headers)
    if key is not None:
        h["Idempotency-Key"] = key
    return client.post(_url(business), headers=h)


def _audit_rows(db: Session, business: Business) -> list[AuditLog]:
    return list(
        db.scalars(
            select(AuditLog).where(
                AuditLog.action == "check.retry", AuditLog.target_id == str(business.id)
            )
        )
    )


def _key_count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(IdempotencyKey)) or 0


@pytest.fixture
def passing(registry: ProviderRegistry) -> ProviderRegistry:
    for p in registry.all():
        p.pass_rate = 1.0
    return registry


def test_missing_and_blank_key_is_400(
    client: TestClient, db: Session, admin_headers: dict[str, str]
) -> None:
    business = make_business(db, checks=FAILED_BVN)
    for key in (None, "   "):
        resp = _post(client, business, admin_headers, key)
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "idempotency_key_required"


@pytest.mark.parametrize("key", ["short", "has space in it!", "x" * 129])
def test_malformed_key_is_422(
    client: TestClient, db: Session, admin_headers: dict[str, str], key: str
) -> None:
    business = make_business(db, checks=FAILED_BVN)
    resp = _post(client, business, admin_headers, key)
    assert resp.status_code == 422
    body = resp.json()["error"]
    assert body["code"] == "validation_error"
    assert body["details"][0]["field"] == "header.Idempotency-Key"


def test_analyst_forbidden(
    client: TestClient, db: Session, analyst_headers: dict[str, str]
) -> None:
    business = make_business(db, checks=FAILED_BVN)
    resp = _post(client, business, analyst_headers, _key())
    assert resp.status_code == 403


def test_unknown_business_and_check_type_404(
    client: TestClient, db: Session, admin_headers: dict[str, str]
) -> None:
    h = {**admin_headers, "Idempotency-Key": _key()}
    missing = client.post(f"/api/v1/businesses/{uuid.uuid4()}/checks/bvn/retry", headers=h)
    assert missing.status_code == 404
    business = make_business(db, checks=FAILED_BVN)
    bad = client.post(f"/api/v1/businesses/{business.id}/checks/passport/retry", headers=h)
    assert bad.status_code == 404
    assert bad.json()["error"]["message"] == "Unknown check type."


def test_check_not_failed_is_409_and_key_released(
    client: TestClient, db: Session, admin_headers: dict[str, str], registry: ProviderRegistry
) -> None:
    business = make_business(db, checks=FAILED_BVN)
    key = _key()
    resp = client.post(_url(business, "cac"), headers={**admin_headers, "Idempotency-Key": key})
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "check_not_retryable"
    assert _key_count(db) == 0
    assert registry.get(ProviderName.cac).verify_calls == 0


def test_happy_path(
    client: TestClient,
    db: Session,
    admin_headers: dict[str, str],
    passing: ProviderRegistry,
) -> None:
    business = make_business(db, checks=FAILED_BVN)
    assert business.stage == Stage.checks_in_progress
    resp = _post(client, business, admin_headers, _key())
    assert resp.status_code == 200
    assert "idempotent-replayed" not in resp.headers
    body = resp.json()
    assert body["replayed"] is False
    assert body["check"]["type"] == "bvn" and body["check"]["status"] == "passed"
    assert body["check"]["failure_reason"] is None and body["check"]["attempts"] == 2
    assert body["business_stage"] == "bank_linked"

    db.refresh(business)
    assert business.stage == Stage.bank_linked
    [audit] = _audit_rows(db, business)
    assert audit.details["check"] == "bvn" and audit.details["result"] == "passed"
    assert audit.details["attempts"] == 2
    stored = db.get(IdempotencyKey, (audit.details["idempotency_key"], audit.actor_id))
    assert (
        stored is not None
        and stored.response_status == 200
        and stored.response
        == {
            **body,
            "replayed": False,
        }
    )


def test_failed_retry_keeps_failure_reason(
    client: TestClient, db: Session, admin_headers: dict[str, str], registry: ProviderRegistry
) -> None:
    for p in registry.all():
        p.pass_rate = 0.0
    business = make_business(db, checks=FAILED_BVN)
    body = _post(client, business, admin_headers, _key()).json()
    assert body["check"]["status"] == "failed" and body["check"]["failure_reason"]
    assert body["business_stage"] == "checks_in_progress"


def test_bank_link_pass_updates_last_sync(
    client: TestClient, db: Session, admin_headers: dict[str, str], passing: ProviderRegistry
) -> None:
    checks = {
        **FAILED_BVN,
        CheckType.bvn: CheckStatus.passed,
        CheckType.bank_link: CheckStatus.failed,
    }
    business = make_business(db, checks=checks)
    assert business.last_bank_sync_at is None
    resp = client.post(
        _url(business, "bank_link"), headers={**admin_headers, "Idempotency-Key": _key()}
    )
    assert resp.status_code == 200
    db.refresh(business)
    assert business.last_bank_sync_at is not None


def test_same_key_twice_replays_without_second_call(
    client: TestClient,
    db: Session,
    admin_headers: dict[str, str],
    passing: ProviderRegistry,
) -> None:
    business = make_business(db, checks=FAILED_BVN)
    key = _key()
    first = _post(client, business, admin_headers, key)
    second = _post(client, business, admin_headers, key)
    assert first.status_code == second.status_code == 200
    assert second.headers["idempotent-replayed"] == "true"
    assert second.json() == {**first.json(), "replayed": True}
    assert passing.get(ProviderName.bvn).verify_calls == 1
    assert len(_audit_rows(db, business)) == 1
    db.refresh(business)
    assert next(c for c in business.checks if c.type == CheckType.bvn).attempts == 2


def test_same_key_on_different_check_is_422(
    client: TestClient, db: Session, admin_headers: dict[str, str], passing: ProviderRegistry
) -> None:
    checks = {**FAILED_BVN, CheckType.tin: CheckStatus.failed}
    business = make_business(db, checks=checks)
    key = _key()
    h = {**admin_headers, "Idempotency-Key": key}
    assert client.post(_url(business, "bvn"), headers=h).status_code == 200
    resp = client.post(_url(business, "tin"), headers=h)
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "idempotency_key_reused"
    assert passing.get(ProviderName.tin).verify_calls == 0


def test_provider_down_is_a_200_failure_then_new_key_reruns(
    client: TestClient, db: Session, admin_headers: dict[str, str], passing: ProviderRegistry
) -> None:
    business = make_business(db, checks=FAILED_BVN)
    passing.get(ProviderName.bvn).set_mode("down")
    resp = _post(client, business, admin_headers, _key())
    assert resp.status_code == 200
    body = resp.json()
    assert body["check"]["status"] == "failed"
    assert body["check"]["failure_reason"] == "Provider unavailable (bvn)"
    assert body["check"]["attempts"] == 2

    passing.get(ProviderName.bvn).set_mode("up")
    again = _post(client, business, admin_headers, _key())
    assert again.json()["check"]["status"] == "passed"
    assert again.json()["check"]["attempts"] == 3


def test_provider_timeout_counts_as_unavailable(
    client: TestClient, db: Session, admin_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.services import retry as retry_mod

    monkeypatch.setattr(retry_mod, "CALL_TIMEOUT_S", 0.05)
    reg = make_registry(sleep=lambda s: asyncio.sleep(1))
    client.app.dependency_overrides[get_registry] = lambda: reg  # type: ignore[attr-defined]
    business = make_business(db, checks=FAILED_BVN)
    body = _post(client, business, admin_headers, _key()).json()
    assert body["check"]["failure_reason"] == "Provider unavailable (bvn)"


class _BrokenProvider(SimulatedProvider):
    async def verify(self, business_id: uuid.UUID, check: CheckType) -> CheckResult:
        self.verify_calls += 1
        if self.verify_calls == 1:
            raise RuntimeError("provider exploded")
        return CheckResult(True, None)


def test_unexpected_provider_error_is_500_and_key_is_released(
    app: Any, db: Session, admin_headers: dict[str, str]
) -> None:
    import random

    from tests.conftest import fast_sleep

    broken = ProviderRegistry(
        [
            (_BrokenProvider if n == ProviderName.bvn else SimulatedProvider)(
                n, random.Random(1), sleep=fast_sleep
            )
            for n in ProviderName
        ]
    )
    app.dependency_overrides[get_registry] = lambda: broken
    business = make_business(db, checks=FAILED_BVN)
    key = _key()
    with TestClient(app, raise_server_exceptions=False) as client:
        first = _post(client, business, admin_headers, key)
        assert first.status_code == 500
        assert first.json()["error"]["code"] == "internal_error"
        assert _key_count(db) == 0
        assert _audit_rows(db, business) == []
        second = _post(client, business, admin_headers, key)
        assert second.status_code == 200
        assert second.json()["check"]["status"] == "passed"


# --- concurrency: needs committed data, so it uses the real test database -----------------


@pytest.fixture
def committed() -> Iterator[tuple[Business, StaffUser]]:
    """Seed committed rows (the double-click race needs two real connections)."""
    with SessionLocal() as s:
        admin = StaffUser(
            id=uuid.uuid4(),
            email="race-admin@credisure.demo",
            password_hash=hash_password("Passw0rd!test"),
            full_name="Race Admin",
            role=Role.ops_admin,
        )
        s.add(admin)
        s.flush()
        business = make_business(s, checks=FAILED_BVN)
        s.commit()
        s.refresh(business)
        s.expunge_all()
    try:
        yield business, admin
    finally:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "TRUNCATE audit_log, idempotency_keys, verification_checks, businesses, "
                    "staff_users RESTART IDENTITY CASCADE"
                )
            )


def test_concurrent_same_key_calls_provider_once(
    committed: tuple[Business, StaffUser],
) -> None:
    business, admin = committed

    async def real_sleep(seconds: float) -> None:
        await asyncio.sleep(0.3)  # the provider call really takes 0.3 s

    registry = make_registry(sleep=real_sleep, pass_rate=1.0)
    app = create_app()  # real get_db: each request gets its own connection
    app.dependency_overrides[get_registry] = lambda: registry
    app.dependency_overrides[get_session_factory] = lambda: SessionLocal

    key = _key()
    barrier = threading.Barrier(2)
    with TestClient(app) as login_client:
        token = login_client.post(
            "/api/v1/auth/login", json={"email": admin.email, "password": "Passw0rd!test"}
        ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": key}

    def fire() -> tuple[int, dict[str, Any]]:
        with TestClient(app) as c:
            barrier.wait(timeout=5)
            resp = c.post(_url(business), headers=headers)
            return resp.status_code, resp.json()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [f.result(timeout=30) for f in [pool.submit(fire), pool.submit(fire)]]

    statuses = sorted(code for code, _ in results)
    assert statuses == [200, 409], results
    ok = next(body for code, body in results if code == 200)
    conflict = next(body for code, body in results if code == 409)
    assert ok["replayed"] is False and ok["check"]["attempts"] == 2
    assert conflict["error"]["code"] == "request_in_progress"
    assert registry.get(ProviderName.bvn).verify_calls == 1
    with SessionLocal() as s:
        audit_count = s.scalar(
            select(func.count()).select_from(AuditLog).where(AuditLog.action == "check.retry")
        )
        assert audit_count == 1
        attempts = s.scalar(text("SELECT attempts FROM verification_checks WHERE type = 'bvn'"))
        assert attempts == 2
