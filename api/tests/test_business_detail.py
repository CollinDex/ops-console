import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import CheckStatus, CheckType
from tests.factories import make_business


def test_detail_masks_identifiers_and_orders_checks(
    client: TestClient, db: Session, analyst_headers: dict[str, str]
) -> None:
    b = make_business(
        db,
        bvn_last4="4321",
        account_last4="8765",
        director_name="Ada Obi",
        checks={CheckType.bvn: CheckStatus.failed},
    )
    resp = client.get(f"/api/v1/businesses/{b.id}", headers=analyst_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "bvn_last4" not in body and "account_last4" not in body
    assert body["bvn_masked"] == "*******4321" and len(body["bvn_masked"]) == 11
    assert body["account_masked"] == "******8765" and len(body["account_masked"]) == 10
    assert body["director_name"] == "Ada Obi"
    assert body["tin"] == b.tin and body["cac_number"] == b.cac_number
    assert [c["type"] for c in body["checks"]] == ["cac", "tin", "bvn", "bank_link"]
    bvn = body["checks"][2]
    assert bvn["status"] == "failed" and bvn["failure_reason"] == "Failed in test"
    assert bvn["attempts"] == 1
    assert body["has_failed_check"] is True


def test_unknown_and_garbage_ids_are_404(
    client: TestClient, analyst_headers: dict[str, str]
) -> None:
    for bad in (str(uuid.uuid4()), "not-a-uuid"):
        resp = client.get(f"/api/v1/businesses/{bad}", headers=analyst_headers)
        assert resp.status_code == 404
        err = resp.json()["error"]
        assert err["code"] == "not_found" and err["message"] == "Business not found."


def test_detail_role_gates(client: TestClient, db: Session, viewer_headers: dict[str, str]) -> None:
    b = make_business(db)
    assert client.get(f"/api/v1/businesses/{b.id}", headers=viewer_headers).status_code == 403
    assert client.get(f"/api/v1/businesses/{b.id}").status_code == 401
