from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, ProviderPing
from app.models.enums import PingStatus, ProviderName
from app.providers.registry import ProviderRegistry


def _ping(
    db: Session,
    provider: ProviderName,
    status: PingStatus,
    minutes_ago: float = 0,
    latency: int | None = 100,
) -> None:
    db.add(
        ProviderPing(
            provider=provider,
            status=status,
            latency_ms=None if status == PingStatus.down else latency,
            error="Connection refused (simulated)" if status == PingStatus.down else None,
            checked_at=datetime.now(UTC) - timedelta(minutes=minutes_ago),
        )
    )
    db.flush()


def test_status_unknown_without_pings(client: TestClient, viewer_headers: dict[str, str]) -> None:
    body = client.get("/api/v1/providers/status", headers=viewer_headers).json()
    assert [p["name"] for p in body["providers"]] == ["bvn", "cac", "tin", "open_banking"]
    assert {p["status"] for p in body["providers"]} == {"unknown"}
    assert body["providers"][0]["uptime_24h"] is None
    assert body["providers"][0]["recent"] == []
    assert body["summary"] == {"up": 0, "slow": 0, "down": 0}


def test_status_shape_and_summary(
    client: TestClient, db: Session, viewer_headers: dict[str, str]
) -> None:
    for i in range(3):
        _ping(db, ProviderName.bvn, PingStatus.up, minutes_ago=10 - i, latency=100 + i * 10)
    _ping(db, ProviderName.bvn, PingStatus.down, minutes_ago=1)
    _ping(db, ProviderName.cac, PingStatus.slow, latency=1500)
    _ping(db, ProviderName.tin, PingStatus.up, latency=90)
    resp = client.get("/api/v1/providers/status", headers=viewer_headers)
    assert resp.status_code == 200
    body = resp.json()
    bvn, cac, tin, ob = body["providers"]
    assert bvn["label"] == "BVN (NIBSS)" and bvn["status"] == "down" and bvn["mode"] == "up"
    assert bvn["latency_ms"] is None
    assert bvn["uptime_24h"] == 75.0
    assert bvn["avg_latency_24h"] == 110
    assert [p["status"] for p in bvn["recent"]] == ["up", "up", "up", "down"]  # oldest first
    assert cac["status"] == "slow" and cac["latency_ms"] == 1500
    assert tin["status"] == "up" and ob["status"] == "unknown"
    assert body["summary"] == {"up": 1, "slow": 1, "down": 1}


def test_recent_is_capped_at_40(
    client: TestClient, db: Session, viewer_headers: dict[str, str]
) -> None:
    for i in range(45):
        _ping(db, ProviderName.bvn, PingStatus.up, minutes_ago=45 - i)
    bvn = client.get("/api/v1/providers/status", headers=viewer_headers).json()["providers"][0]
    assert len(bvn["recent"]) == 40


def test_status_requires_auth(client: TestClient) -> None:
    assert client.get("/api/v1/providers/status").status_code == 401


def test_viewer_cannot_simulate(client: TestClient, viewer_headers: dict[str, str]) -> None:
    resp = client.post(
        "/api/v1/providers/bvn/simulate", json={"mode": "down"}, headers=viewer_headers
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "forbidden"


def test_simulate_sets_mode_audits_and_pings(
    client: TestClient,
    db: Session,
    admin_headers: dict[str, str],
    registry: ProviderRegistry,
) -> None:
    resp = client.post(
        "/api/v1/providers/bvn/simulate", json={"mode": "down"}, headers=admin_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "bvn" and body["mode"] == "down" and body["status"] == "down"
    assert registry.get(ProviderName.bvn).mode == "down"

    audit = db.scalars(select(AuditLog).where(AuditLog.action == "provider.simulate")).one()
    assert (audit.target_type, audit.target_id) == ("provider", "bvn")
    assert audit.details == {"from": "up", "to": "down"}
    ping = db.scalars(select(ProviderPing).where(ProviderPing.provider == ProviderName.bvn)).one()
    assert ping.status == PingStatus.down and ping.error

    status = client.get("/api/v1/providers/status", headers=admin_headers).json()
    assert status["providers"][0]["status"] == "down"


def test_simulate_validates_mode_and_name(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    bad_mode = client.post(
        "/api/v1/providers/bvn/simulate", json={"mode": "broken"}, headers=admin_headers
    )
    assert bad_mode.status_code == 422
    unknown = client.post(
        "/api/v1/providers/nope/simulate", json={"mode": "up"}, headers=admin_headers
    )
    assert unknown.status_code == 404


def test_health_degraded_when_provider_down(client: TestClient, db: Session) -> None:
    ok = client.get("/health").json()
    assert ok["status"] == "ok" and ok["providers"] == {"up": 0, "slow": 0, "down": 0}
    _ping(db, ProviderName.tin, PingStatus.up)
    _ping(db, ProviderName.bvn, PingStatus.down)
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "degraded" and body["db"] == "ok"
    assert body["providers"] == {"up": 1, "slow": 0, "down": 1}


def test_incidents_endpoint(
    client: TestClient, db: Session, viewer_headers: dict[str, str]
) -> None:
    _ping(db, ProviderName.bvn, PingStatus.up, minutes_ago=30)
    _ping(db, ProviderName.bvn, PingStatus.down, minutes_ago=20)
    _ping(db, ProviderName.bvn, PingStatus.slow, minutes_ago=19)
    _ping(db, ProviderName.bvn, PingStatus.up, minutes_ago=18)
    _ping(db, ProviderName.bvn, PingStatus.down, minutes_ago=2)
    # An older-than-7-days incident is outside the window.
    _ping(db, ProviderName.bvn, PingStatus.down, minutes_ago=60 * 24 * 9)
    resp = client.get("/api/v1/providers/bvn/incidents", headers=viewer_headers)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 2
    assert items[0]["ended_at"] is None and items[0]["worst_status"] == "down"  # newest first
    assert items[1]["ping_count"] == 2 and items[1]["duration_seconds"] == 120


def test_incidents_unknown_provider(client: TestClient, viewer_headers: dict[str, str]) -> None:
    resp = client.get("/api/v1/providers/nope/incidents", headers=viewer_headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"
