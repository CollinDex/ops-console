from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.db.session import engine
from app.models.enums import CheckStatus, CheckType, Sector, Stage
from tests.factories import make_business

URL = "/api/v1/businesses"
FAILED = CheckStatus.failed
PASSED = CheckStatus.passed


def names(resp_json: dict) -> list[str]:  # type: ignore[type-arg]
    return [i["name"] for i in resp_json["items"]]


def test_pagination_total_and_last_partial_page(
    client: TestClient, db: Session, analyst_headers: dict[str, str]
) -> None:
    for _ in range(25):
        make_business(db)
    first = client.get(URL, params={"page_size": 10}, headers=analyst_headers).json()
    assert first["total"] == 25 and first["page"] == 1 and first["page_size"] == 10
    assert len(first["items"]) == 10
    last = client.get(URL, params={"page_size": 10, "page": 3}, headers=analyst_headers).json()
    assert len(last["items"]) == 5


def test_page_past_the_end_is_empty_with_real_total(
    client: TestClient, db: Session, analyst_headers: dict[str, str]
) -> None:
    for _ in range(3):
        make_business(db)
    body = client.get(URL, params={"page": 9}, headers=analyst_headers).json()
    assert body["items"] == [] and body["total"] == 3


def test_default_sort_is_newest_first_and_name_asc_works(
    client: TestClient, db: Session, analyst_headers: dict[str, str]
) -> None:
    now = datetime.now(UTC)
    make_business(db, name="Bravo", created_at=now - timedelta(days=3))
    make_business(db, name="Alpha", created_at=now - timedelta(days=5))
    make_business(db, name="Charlie", created_at=now - timedelta(days=1))
    assert names(client.get(URL, headers=analyst_headers).json()) == ["Charlie", "Bravo", "Alpha"]
    asc = client.get(URL, params={"sort": "name", "order": "asc"}, headers=analyst_headers)
    assert names(asc.json()) == ["Alpha", "Bravo", "Charlie"]


def test_nulls_last_in_both_directions(
    client: TestClient, db: Session, analyst_headers: dict[str, str]
) -> None:
    make_business(db, name="NoScore", credit_score=None)
    make_business(db, name="Low", credit_score=400)
    make_business(db, name="High", credit_score=800)
    for order, expected in (
        ("asc", ["Low", "High", "NoScore"]),
        ("desc", ["High", "Low", "NoScore"]),
    ):
        resp = client.get(
            URL, params={"sort": "credit_score", "order": order}, headers=analyst_headers
        )
        assert names(resp.json()) == expected
    sync = datetime.now(UTC)
    make_business(db, name="Synced", last_bank_sync_at=sync)
    resp = client.get(
        URL, params={"sort": "last_bank_sync_at", "order": "desc"}, headers=analyst_headers
    )
    assert names(resp.json())[0] == "Synced"


def test_sort_is_stable_across_pages_when_values_tie(
    client: TestClient, db: Session, analyst_headers: dict[str, str]
) -> None:
    for _ in range(12):
        make_business(db, credit_score=600)
    seen: list[str] = []
    for page in (1, 2, 3, 4):
        resp = client.get(
            URL,
            params={"sort": "credit_score", "page_size": 5, "page": page},
            headers=analyst_headers,
        )
        seen += [i["id"] for i in resp.json()["items"]]
    assert len(seen) == 12 and len(set(seen)) == 12


def test_search_by_name_director_and_cac_prefix(
    client: TestClient, db: Session, analyst_headers: dict[str, str]
) -> None:
    make_business(
        db, name="Adebayo Agro Ventures", director_name="Tunde Bello", cac_number="RC900001"
    )
    make_business(db, name="Zenith Logistics", director_name="Ngozi Eze", cac_number="RC900002")

    def found(term: str) -> list[str]:
        return names(client.get(URL, params={"search": term}, headers=analyst_headers).json())

    assert found("agro") == ["Adebayo Agro Ventures"]
    assert found("  AGRO  ") == ["Adebayo Agro Ventures"]
    assert found("ngozi") == ["Zenith Logistics"]
    assert found("rc90000") != [] and len(found("rc90000")) == 2
    assert found("rc900002") == ["Zenith Logistics"]
    assert found("900002") == []  # CAC is a prefix match, not a substring match
    assert len(found("")) == 2  # empty search means no search


def test_search_treats_percent_and_underscore_literally(
    client: TestClient, db: Session, analyst_headers: dict[str, str]
) -> None:
    make_business(db, name="100% Organic")
    make_business(db, name="Plain Name")
    make_business(db, name="Snake_Case Ltd")
    make_business(db, name="SnakeXCase Ltd")

    def found(term: str) -> list[str]:
        return names(client.get(URL, params={"search": term}, headers=analyst_headers).json())

    assert found("%") == ["100% Organic"]
    assert found("_") == ["Snake_Case Ltd"]
    assert found("\\") == []


def test_search_longer_than_100_chars_is_422(
    client: TestClient, analyst_headers: dict[str, str]
) -> None:
    resp = client.get(URL, params={"search": "x" * 101}, headers=analyst_headers)
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"
    assert client.get(URL, params={"search": "x" * 100}, headers=analyst_headers).status_code == 200


def test_filters_each_alone(
    client: TestClient, db: Session, analyst_headers: dict[str, str]
) -> None:
    make_business(db, name="A", stage=Stage.signed_up, sector=Sector.retail, credit_score=350)
    make_business(db, name="B", stage=Stage.bank_linked, sector=Sector.fashion, credit_score=700)
    make_business(db, name="C", stage=Stage.bank_linked, sector=Sector.retail, credit_score=None)

    def found(**params: object) -> set[str]:
        return set(names(client.get(URL, params=params, headers=analyst_headers).json()))

    assert found(stage="bank_linked") == {"B", "C"}
    assert found(stage=["signed_up", "bank_linked"]) == {"A", "B", "C"}
    assert found(sector="fashion") == {"B"}
    assert found(sector=["fashion", "retail"]) == {"A", "B", "C"}
    assert found(score_min=700) == {"B"}  # inclusive, and NULL score excluded
    assert found(score_max=350) == {"A"}
    assert found(score_min=350, score_max=700) == {"A", "B"}


def test_failed_check_any_vs_specific(
    client: TestClient, db: Session, analyst_headers: dict[str, str]
) -> None:
    make_business(db, name="BvnFail", checks={CheckType.bvn: FAILED, CheckType.cac: PASSED})
    make_business(db, name="TinFail", checks={CheckType.tin: FAILED})
    make_business(db, name="Clean", checks={CheckType.cac: PASSED})

    def found(value: str) -> set[str]:
        resp = client.get(URL, params={"failed_check": value}, headers=analyst_headers)
        return set(names(resp.json()))

    assert found("any") == {"BvnFail", "TinFail"}
    assert found("bvn") == {"BvnFail"}
    assert found("tin") == {"TinFail"}
    assert found("cac") == set()


def test_combined_filters(client: TestClient, db: Session, analyst_headers: dict[str, str]) -> None:
    make_business(
        db,
        name="Match",
        stage=Stage.checks_in_progress,
        sector=Sector.retail,
        credit_score=600,
        checks={CheckType.bvn: FAILED},
    )
    make_business(
        db,
        name="WrongStage",
        stage=Stage.bank_linked,
        sector=Sector.retail,
        credit_score=600,
        checks={CheckType.bvn: FAILED},
    )
    make_business(
        db,
        name="WrongScore",
        stage=Stage.checks_in_progress,
        sector=Sector.retail,
        credit_score=800,
        checks={CheckType.bvn: FAILED},
    )
    make_business(
        db, name="NoFail", stage=Stage.checks_in_progress, sector=Sector.retail, credit_score=600
    )
    resp = client.get(
        URL,
        params={
            "stage": "checks_in_progress",
            "sector": "retail",
            "score_min": 500,
            "score_max": 700,
            "failed_check": "bvn",
        },
        headers=analyst_headers,
    )
    assert names(resp.json()) == ["Match"] and resp.json()["total"] == 1


def test_item_shape_checks_and_stale_flag(
    client: TestClient, db: Session, analyst_headers: dict[str, str]
) -> None:
    now = datetime.now(UTC)
    make_business(
        db,
        name="Stale",
        last_bank_sync_at=now - timedelta(days=9),
        checks={CheckType.bank_link: PASSED, CheckType.bvn: FAILED},
    )
    make_business(
        db,
        name="Fresh",
        last_bank_sync_at=now - timedelta(days=2),
        checks={CheckType.bank_link: PASSED},
    )
    make_business(
        db,
        name="OldNotPassed",
        last_bank_sync_at=now - timedelta(days=20),
        checks={CheckType.bank_link: FAILED},
    )
    items = {i["name"]: i for i in client.get(URL, headers=analyst_headers).json()["items"]}
    assert items["Stale"]["bank_data_stale"] is True
    assert items["Stale"]["has_failed_check"] is True
    assert items["Stale"]["checks"] == {
        "cac": "pending",
        "tin": "pending",
        "bvn": "failed",
        "bank_link": "passed",
    }
    assert items["Fresh"]["bank_data_stale"] is False
    assert items["Fresh"]["has_failed_check"] is False
    assert items["OldNotPassed"]["bank_data_stale"] is False
    assert "bvn_last4" not in items["Stale"] and "tin" not in items["Stale"]


def test_validation_errors(client: TestClient, analyst_headers: dict[str, str]) -> None:
    resp = client.get(URL, params={"score_min": 700, "score_max": 400}, headers=analyst_headers)
    assert resp.status_code == 422
    err = resp.json()["error"]
    assert err["code"] == "validation_error"
    assert err["details"][0]["field"] == "score_min"
    for params in (
        {"stage": "nope"},
        {"sort": "tin"},
        {"order": "sideways"},
        {"failed_check": "x"},
        {"score_min": 100},
        {"page": 0},
        {"page_size": 101},
    ):
        bad = client.get(URL, params=params, headers=analyst_headers)
        assert bad.status_code == 422, params
        assert bad.json()["error"]["code"] == "validation_error"


def test_viewer_403_and_anonymous_401(client: TestClient, viewer_headers: dict[str, str]) -> None:
    resp = client.get(URL, headers=viewer_headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["message"] == "Your role (viewer) cannot view businesses."
    assert client.get(URL).status_code == 401


def test_list_query_count_does_not_grow_with_page_size(
    client: TestClient, db: Session, analyst_headers: dict[str, str]
) -> None:
    for _ in range(50):
        make_business(db, checks={CheckType.cac: PASSED})
    statements: list[str] = []

    def record(conn, cursor, statement, parameters, context, executemany):  # type: ignore[no-untyped-def]
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    try:
        resp = client.get(URL, params={"page_size": 50}, headers=analyst_headers)
    finally:
        event.remove(engine, "before_cursor_execute", record)
    assert resp.status_code == 200 and len(resp.json()["items"]) == 50
    business_queries = [s for s in statements if "staff_users" not in s]
    # count, page, checks. The staff_users lookup is the auth check.
    assert len(business_queries) <= 3, business_queries
    assert len(statements) <= 4
