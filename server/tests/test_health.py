"""Health and readiness endpoint tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from loaded_dicewriter.app import create_app
from loaded_dicewriter.settings import clear_settings_cache


def test_healthz_ok() -> None:
    clear_settings_cache()
    client = TestClient(create_app())
    res = client.get("/api/healthz")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_readyz_distinguishes_app_and_model() -> None:
    clear_settings_cache()
    client = TestClient(create_app())
    res = client.get("/api/readyz")
    assert res.status_code == 200
    body = res.json()
    assert "app_ready" in body
    assert "model_ready" in body
    assert "ready" in body
    assert body["app_ready"] is True
    # Default fake mode is model-ready without GPU/weights.
    assert body["model_ready"] is True
    assert body["ready"] is True
    assert body["model_mode"] == "fake"


def test_status_fake_mode() -> None:
    clear_settings_cache()
    client = TestClient(create_app())
    res = client.get("/api/status")
    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "loaded-dicewriter"
    assert body["model_mode"] == "fake"
    assert body["telemetry"] is False
    assert body["fake_sample"]
