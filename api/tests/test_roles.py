import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import require_roles
from app.models import StaffUser
from app.models.enums import Role
from tests.factories import auth_header, make_staff

PASSWORD = "Passw0rd!test"


@pytest.fixture
def role_client(app: FastAPI) -> TestClient:
    @app.post("/test/rerun")
    def rerun(
        user: StaffUser = Depends(require_roles(Role.ops_admin, action="re-run checks")),  # noqa: B008
    ) -> dict[str, str]:
        return {"who": user.email}

    return TestClient(app)


def test_viewer_is_forbidden(role_client: TestClient, db: Session) -> None:
    viewer = make_staff(db, role=Role.viewer, password=PASSWORD)
    resp = role_client.post("/test/rerun", headers=auth_header(role_client, viewer.email, PASSWORD))
    assert resp.status_code == 403
    err = resp.json()["error"]
    assert err["code"] == "forbidden"
    assert err["message"] == "Your role (viewer) cannot re-run checks."


def test_ops_admin_is_allowed(role_client: TestClient, db: Session) -> None:
    admin = make_staff(db, role=Role.ops_admin, password=PASSWORD)
    resp = role_client.post("/test/rerun", headers=auth_header(role_client, admin.email, PASSWORD))
    assert resp.status_code == 200
    assert resp.json() == {"who": admin.email}


def test_role_name_underscores_become_spaces(role_client: TestClient, db: Session) -> None:
    analyst = make_staff(db, role=Role.analyst, password=PASSWORD)
    resp = role_client.post(
        "/test/rerun", headers=auth_header(role_client, analyst.email, PASSWORD)
    )
    assert resp.json()["error"]["message"] == "Your role (analyst) cannot re-run checks."


def test_anonymous_gets_401_before_role_check(role_client: TestClient) -> None:
    resp = role_client.post("/test/rerun")
    assert resp.status_code == 401
