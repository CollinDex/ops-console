import io
import json
import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.logging import JsonFormatter


def test_unknown_route_returns_envelope(client: TestClient) -> None:
    resp = client.get("/api/v1/nope")
    assert resp.status_code == 404
    err = resp.json()["error"]
    assert err["code"] == "not_found"
    assert err["request_id"] == resp.headers["X-Request-ID"]


def test_wrong_method_returns_envelope(client: TestClient) -> None:
    resp = client.get("/api/v1/auth/login")
    assert resp.status_code == 405
    assert resp.json()["error"]["code"] == "method_not_allowed"


def test_request_id_is_echoed(client: TestClient) -> None:
    resp = client.get("/api/v1/nope", headers={"X-Request-ID": "abc123"})
    assert resp.headers["X-Request-ID"] == "abc123"
    assert resp.json()["error"]["request_id"] == "abc123"


def test_request_id_is_generated(client: TestClient) -> None:
    resp = client.get("/health")
    assert len(resp.headers["X-Request-ID"]) == 32


def test_unhandled_exception_returns_generic_500(
    app: FastAPI, caplog: pytest.LogCaptureFixture
) -> None:
    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("secret internal detail")

    with caplog.at_level(logging.ERROR), TestClient(app) as c:
        resp = c.get("/boom", headers={"X-Request-ID": "req-500"})
    assert resp.status_code == 500
    body = resp.json()
    assert body["error"]["code"] == "internal_error"
    assert body["error"]["request_id"] == "req-500"
    assert "secret internal detail" not in resp.text
    assert "Traceback" not in resp.text
    assert any(
        r.exc_info and "secret internal detail" in str(r.exc_info[1]) for r in caplog.records
    )


def test_access_log_is_json_with_request_id(client: TestClient) -> None:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())  # formatted while the request context is live
    access = logging.getLogger("app.access")
    access.addHandler(handler)
    try:
        client.get("/health", headers={"X-Request-ID": "log-1"})
    finally:
        access.removeHandler(handler)
    line = json.loads(stream.getvalue().splitlines()[0])
    assert line["msg"] == "request"
    assert line["request_id"] == "log-1"
    assert line["method"] == "GET" and line["path"] == "/health" and line["status"] == 200
    assert "duration_ms" in line
