import itertools
import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import Business, StaffUser, VerificationCheck
from app.models.enums import CheckStatus, CheckType, Role, Sector, Stage

_counter = itertools.count(1)


def make_staff(
    db: Session,
    role: Role = Role.analyst,
    password: str = "Passw0rd!test",
    email: str | None = None,
    full_name: str = "Test User",
) -> StaffUser:
    n = next(_counter)
    user = StaffUser(
        id=uuid.uuid4(),
        email=email or f"user{n}@credisure.demo",
        password_hash=hash_password(password),
        full_name=full_name,
        role=role,
    )
    db.add(user)
    db.flush()
    return user


def make_business(
    db: Session,
    stage: Stage = Stage.checks_in_progress,
    checks: dict[CheckType, CheckStatus] | None = None,
    **overrides: object,
) -> Business:
    n = next(_counter)
    now = datetime.now(UTC)
    values: dict[str, object] = {
        "id": uuid.uuid4(),
        "name": f"Test Business {n} Ltd",
        "cac_number": f"RC{100000 + n}",
        "tin": f"{10000000 + n}-0001",
        "sector": Sector.retail,
        "state": "Lagos",
        "director_name": "Ada Obi",
        "bvn_last4": "1234",
        "bank_name": "GTBank",
        "account_last4": "5678",
        "stage": stage,
        "created_at": now - timedelta(days=10),
    }
    values.update(overrides)
    business = Business(**values)
    db.add(business)
    db.flush()
    statuses = checks or dict.fromkeys(CheckType, CheckStatus.pending)
    for check_type in CheckType:
        status = statuses.get(check_type, CheckStatus.pending)
        db.add(
            VerificationCheck(
                business_id=business.id,
                type=check_type,
                status=status,
                failure_reason="Failed in test" if status == CheckStatus.failed else None,
                attempts=0 if status == CheckStatus.pending else 1,
            )
        )
    db.flush()
    db.refresh(business)
    return business


def auth_header(client: TestClient, email: str, password: str) -> dict[str, str]:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
