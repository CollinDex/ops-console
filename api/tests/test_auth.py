from datetime import UTC, datetime, timedelta

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token
from app.models import AuditLog
from app.models.enums import Role
from tests.factories import make_staff

PASSWORD = "Passw0rd!test"


def _login(client: TestClient, email: str, password: str):  # type: ignore[no-untyped-def]
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def test_login_success(client: TestClient, db: Session) -> None:
    user = make_staff(db, role=Role.ops_admin, password=PASSWORD)
    resp = _login(client, user.email, PASSWORD)
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["user"] == {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": "ops_admin",
    }
    claims = jwt.decode(body["access_token"], get_settings().jwt_secret, algorithms=["HS256"])
    assert claims["role"] == "ops_admin"
    assert claims["sub"] == str(user.id)
    assert claims["jti"]
    minutes_left = (
        datetime.fromtimestamp(claims["exp"], UTC) - datetime.now(UTC)
    ).total_seconds() / 60
    assert 58 < minutes_left <= 60


def test_login_email_is_case_insensitive(client: TestClient, db: Session) -> None:
    user = make_staff(db, password=PASSWORD)
    assert _login(client, user.email.upper(), PASSWORD).status_code == 200


def test_wrong_password_and_unknown_email_are_indistinguishable(
    client: TestClient, db: Session
) -> None:
    user = make_staff(db, password=PASSWORD)
    wrong = _login(client, user.email, "not-the-password")
    unknown = _login(client, "nobody@credisure.demo", PASSWORD)
    assert wrong.status_code == unknown.status_code == 401
    for resp in (wrong, unknown):
        err = resp.json()["error"]
        assert err["code"] == "invalid_credentials"
        assert err["message"] == "Email or password is incorrect."
        assert err["request_id"]


def test_login_validation_errors(client: TestClient) -> None:
    resp = _login(client, "not-an-email", "")
    assert resp.status_code == 422
    err = resp.json()["error"]
    assert err["code"] == "validation_error"
    fields = {d["field"] for d in err["details"]}
    assert {"body.email", "body.password"} <= fields


def test_over_long_password_is_rejected_cleanly(client: TestClient, db: Session) -> None:
    user = make_staff(db, password=PASSWORD)
    assert _login(client, user.email, "x" * 100).status_code == 401  # over bcrypt's 72 bytes
    assert _login(client, user.email, "x" * 129).status_code == 422


def test_me_requires_a_token(client: TestClient) -> None:
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "not_authenticated"


def test_me_rejects_garbage_token(client: TestClient) -> None:
    resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer garbage"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "not_authenticated"


def test_me_rejects_expired_token(client: TestClient, db: Session) -> None:
    user = make_staff(db)
    token, _ = create_access_token(user, ttl_minutes=-1)
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "token_expired"


def test_me_rejects_token_signed_with_another_secret(client: TestClient, db: Session) -> None:
    user = make_staff(db)
    forged = jwt.encode(
        {"sub": str(user.id), "exp": datetime.now(UTC) + timedelta(hours=1)},
        "another-secret-another-secret-123",
        algorithm="HS256",
    )
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "not_authenticated"


def test_me_rejects_token_for_deleted_user(client: TestClient, db: Session) -> None:
    user = make_staff(db)
    token, _ = create_access_token(user)
    db.delete(user)
    db.flush()
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_me_with_valid_token(client: TestClient, db: Session) -> None:
    user = make_staff(db, role=Role.viewer, password=PASSWORD)
    token = _login(client, user.email, PASSWORD).json()["access_token"]
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == user.email
    assert resp.json()["role"] == "viewer"


def test_role_comes_from_db_not_token(client: TestClient, db: Session) -> None:
    user = make_staff(db, role=Role.ops_admin, password=PASSWORD)
    token = _login(client, user.email, PASSWORD).json()["access_token"]
    user.role = Role.viewer
    db.flush()
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.json()["role"] == "viewer"


def test_login_writes_audit_rows(client: TestClient, db: Session) -> None:
    user = make_staff(db, password=PASSWORD)
    _login(client, user.email, PASSWORD)
    _login(client, "Ghost@Credisure.demo", "whatever")
    rows = list(db.scalars(select(AuditLog).order_by(AuditLog.id)))
    assert [r.action for r in rows] == ["login.success", "login.failure"]
    assert rows[0].actor_id == user.id
    assert rows[1].actor_id is None
    assert rows[1].details == {"email": "ghost@credisure.demo"}
    assert "whatever" not in str(rows[1].details)
