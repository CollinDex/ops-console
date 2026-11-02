from fastapi.testclient import TestClient


def test_meta_shape(client: TestClient, analyst_headers: dict[str, str]) -> None:
    body = client.get("/api/v1/meta/filters", headers=analyst_headers).json()
    assert [s["value"] for s in body["stages"]] == [
        "signed_up",
        "documents_submitted",
        "checks_in_progress",
        "bank_linked",
        "profile_ready",
    ]
    assert body["stages"][0] == {"value": "signed_up", "label": "Signed up"}
    labels = [s["label"] for s in body["sectors"]]
    assert labels == sorted(labels) and len(labels) == 10
    assert body["check_types"] == [
        {"value": "cac", "label": "CAC"},
        {"value": "tin", "label": "Tax ID"},
        {"value": "bvn", "label": "BVN"},
        {"value": "bank_link", "label": "Bank link"},
    ]
    bands = body["score_bands"]
    assert [b["key"] for b in bands] == ["poor", "fair", "good", "very_good", "excellent"]
    assert bands[0] == {"key": "poor", "label": "Poor", "min": 300, "max": 579}
    assert bands[-1]["max"] == 850


def test_meta_role_gates(client: TestClient, viewer_headers: dict[str, str]) -> None:
    assert client.get("/api/v1/meta/filters", headers=viewer_headers).status_code == 403
    assert client.get("/api/v1/meta/filters").status_code == 401
