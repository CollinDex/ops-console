from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import Role
from tests.factories import make_staff

URL = "/api/v1/staff"


def test_staff_shape_has_no_password_hash(
    client: TestClient, db: Session, analyst_headers: dict[str, str]
) -> None:
    body = client.get(URL, headers=analyst_headers).json()
    assert body["total"] == 1 and body["page"] == 1 and body["page_size"] == 20
    item = body["items"][0]
    assert set(item) == {"id", "email", "full_name", "role", "created_at"}
    assert "password_hash" not in client.get(URL, headers=analyst_headers).text


def test_staff_search_role_sort_paginate(
    client: TestClient, db: Session, analyst_headers: dict[str, str]
) -> None:
    make_staff(db, role=Role.viewer, full_name="Zara Yusuf", email="zara@credisure.demo")
    make_staff(db, role=Role.ops_admin, full_name="Amaka Obi", email="amaka@credisure.demo")
    make_staff(db, role=Role.viewer, full_name="Bola 100%", email="bola@credisure.demo")

    def get(**params: object) -> dict:  # type: ignore[type-arg]
        return client.get(URL, params=params, headers=analyst_headers).json()

    assert [i["full_name"] for i in get(search="zara")["items"]] == ["Zara Yusuf"]
    assert [i["full_name"] for i in get(search="AMAKA@")["items"]] == ["Amaka Obi"]
    assert [i["full_name"] for i in get(search="%")["items"]] == ["Bola 100%"]
    assert {i["role"] for i in get(role="viewer")["items"]} == {"viewer"}
    assert get(role=["viewer", "ops_admin"])["total"] == 3
    names = [i["full_name"] for i in get(sort="full_name", order="desc")["items"]]
    assert names == sorted(names, reverse=True)
    page2 = get(page_size=2, page=2)
    assert page2["total"] == 4 and len(page2["items"]) == 2


def test_staff_role_gates(client: TestClient, viewer_headers: dict[str, str]) -> None:
    resp = client.get(URL, headers=viewer_headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["message"] == "Your role (viewer) cannot view the team."
    assert client.get(URL).status_code == 401
