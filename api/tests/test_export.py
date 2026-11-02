import csv
import io

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog
from app.models.enums import CheckStatus, CheckType, Sector
from app.services import businesses as svc
from tests.factories import make_business

URL = "/api/v1/businesses/export.csv"


def parse(text: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(text)))


def test_export_header_filters_and_disposition(
    client: TestClient, db: Session, analyst_headers: dict[str, str]
) -> None:
    make_business(
        db,
        name="Farm One",
        sector=Sector.agriculture,
        director_name="Secret Person",
        checks={CheckType.cac: CheckStatus.passed},
    )
    make_business(db, name="Shop One", sector=Sector.retail)
    resp = client.get(URL, params={"sector": "agriculture"}, headers=analyst_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "text/csv; charset=utf-8"
    disposition = resp.headers["content-disposition"]
    assert disposition.startswith('attachment; filename="credisure-businesses-')
    assert disposition.endswith('.csv"')
    assert "x-truncated" not in resp.headers
    assert resp.text.splitlines()[0] == ",".join(svc.EXPORT_COLUMNS)
    rows = parse(resp.text)
    assert len(rows) == 1 and rows[0]["name"] == "Farm One"
    assert rows[0]["cac"] == "passed" and rows[0]["tin"] == "pending"
    assert "Secret Person" not in resp.text and "1234" not in resp.text


def test_export_writes_audit_row(
    client: TestClient, db: Session, analyst_headers: dict[str, str]
) -> None:
    make_business(db, sector=Sector.agriculture)
    client.get(URL, params={"sector": "agriculture", "search": "Test"}, headers=analyst_headers)
    audit = db.scalars(select(AuditLog).where(AuditLog.action == "businesses.export")).one()
    assert audit.actor_id is not None
    assert audit.details == {"filters": {"search": "Test", "sector": ["agriculture"]}, "rows": 1}


def test_export_neutralises_formula_cells(
    client: TestClient, db: Session, analyst_headers: dict[str, str]
) -> None:
    make_business(db, name="=HYPERLINK(1)")
    assert parse(client.get(URL, headers=analyst_headers).text)[0]["name"] == "'=HYPERLINK(1)"


def test_export_truncates_at_cap(
    client: TestClient,
    db: Session,
    analyst_headers: dict[str, str],
    monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    monkeypatch.setattr(svc, "EXPORT_ROW_CAP", 2)
    for _ in range(3):
        make_business(db)
    resp = client.get(URL, headers=analyst_headers)
    assert resp.headers["x-truncated"] == "true" and len(parse(resp.text)) == 2


def test_export_route_is_not_swallowed_by_id(
    client: TestClient, analyst_headers: dict[str, str]
) -> None:
    assert client.get(URL, headers=analyst_headers).status_code == 200


def test_viewer_403_anonymous_401(client: TestClient, viewer_headers: dict[str, str]) -> None:
    assert client.get(URL, headers=viewer_headers).status_code == 403
    assert client.get(URL).status_code == 401
