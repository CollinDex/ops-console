import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import AuditLog
from app.models.enums import Role
from tests.factories import make_business, make_staff


def _audit(
    db: Session, business_id: uuid.UUID, actor_id: uuid.UUID | None, action: str, minutes_ago: int
) -> None:
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            target_type="business",
            target_id=str(business_id),
            details={"n": minutes_ago},
            created_at=datetime.now(UTC) - timedelta(minutes=minutes_ago),
        )
    )
    db.flush()


def test_audit_newest_first_with_actor(
    client: TestClient, db: Session, analyst_headers: dict[str, str]
) -> None:
    business = make_business(db)
    other = make_business(db)
    admin = make_staff(db, role=Role.ops_admin, full_name="Ada Admin")
    _audit(db, business.id, admin.id, "check.retry", 30)
    _audit(db, business.id, None, "system.sync", 10)
    _audit(db, other.id, admin.id, "check.retry", 5)  # other business: excluded
    resp = client.get(f"/api/v1/businesses/{business.id}/audit", headers=analyst_headers)
    assert resp.status_code == 200
    items = resp.json()
    assert [i["action"] for i in items] == ["system.sync", "check.retry"]
    assert items[0]["actor"] is None
    assert items[1]["actor"] == {"id": str(admin.id), "full_name": "Ada Admin", "role": "ops_admin"}
    assert items[1]["details"] == {"n": 30}


def test_audit_limited_to_50(
    client: TestClient, db: Session, analyst_headers: dict[str, str]
) -> None:
    business = make_business(db)
    for i in range(55):
        _audit(db, business.id, None, "x", i)
    items = client.get(f"/api/v1/businesses/{business.id}/audit", headers=analyst_headers).json()
    assert len(items) == 50


def test_audit_unknown_business_404(client: TestClient, analyst_headers: dict[str, str]) -> None:
    resp = client.get(
        "/api/v1/businesses/00000000-0000-0000-0000-000000000000/audit", headers=analyst_headers
    )
    assert resp.status_code == 404


def test_audit_viewer_forbidden(
    client: TestClient, db: Session, viewer_headers: dict[str, str]
) -> None:
    business = make_business(db)
    resp = client.get(f"/api/v1/businesses/{business.id}/audit", headers=viewer_headers)
    assert resp.status_code == 403


def test_audit_has_no_mutation_routes(
    client: TestClient, db: Session, admin_headers: dict[str, str]
) -> None:
    business = make_business(db)
    url = f"/api/v1/businesses/{business.id}/audit"
    for method in ("put", "patch", "delete"):
        resp = getattr(client, method)(url, headers=admin_headers)
        assert resp.status_code == 405, method
