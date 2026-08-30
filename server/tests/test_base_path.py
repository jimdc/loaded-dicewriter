"""APP_BASE_PATH: hub subpath hosting (`/loaded-dicewriter/`) and root default."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from loaded_dicewriter.base_path import AppBasePathMiddleware
from loaded_dicewriter.settings import (
    app_base_prefix,
    clear_settings_cache,
    normalize_app_base_path,
)


def test_normalize_app_base_path() -> None:
    assert normalize_app_base_path(None) == "/"
    assert normalize_app_base_path("") == "/"
    assert normalize_app_base_path("/") == "/"
    assert normalize_app_base_path("/loaded-dicewriter") == "/loaded-dicewriter/"
    assert normalize_app_base_path("/loaded-dicewriter/") == "/loaded-dicewriter/"
    assert normalize_app_base_path("loaded-dicewriter") == "/loaded-dicewriter/"
    assert normalize_app_base_path("loaded-dicewriter/") == "/loaded-dicewriter/"


def test_app_base_prefix() -> None:
    assert app_base_prefix("/") == ""
    assert app_base_prefix("/loaded-dicewriter/") == "/loaded-dicewriter"
    assert app_base_prefix("/loaded-dicewriter") == "/loaded-dicewriter"


def test_base_path_middleware_strips_prefix_and_keeps_root_probes() -> None:
    app = FastAPI()
    app.add_middleware(AppBasePathMiddleware, base_path="/loaded-dicewriter/")

    @app.get("/api/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/status")
    def status() -> dict[str, str]:
        return {"name": "loaded-dicewriter"}

    client = TestClient(app)

    # Unprefixed probes stay on the root for gateway health checks.
    assert client.get("/api/healthz").status_code == 200
    assert client.get("/api/healthz").json() == {"status": "ok"}

    # Prefixed API paths rewrite to internal routes.
    res = client.get("/loaded-dicewriter/api/status")
    assert res.status_code == 200
    assert res.json() == {"name": "loaded-dicewriter"}
    assert client.get("/loaded-dicewriter/api/healthz").json() == {"status": "ok"}

    # Root-mounted routes still answer (gateway-stripped traffic).
    assert client.get("/api/status").json() == {"name": "loaded-dicewriter"}


def test_base_path_middleware_noop_at_root() -> None:
    app = FastAPI()
    app.add_middleware(AppBasePathMiddleware, base_path="/")

    @app.get("/api/status")
    def status() -> list[dict[str, bool]]:
        return [{"ok": True}]

    client = TestClient(app)
    assert client.get("/api/status").json() == [{"ok": True}]
    # No strip: a literal /loaded-dicewriter/... path is not rewritten.
    assert client.get("/loaded-dicewriter/api/status").status_code == 404


def test_settings_reads_app_base_path_env(monkeypatch: object) -> None:
    from _pytest.monkeypatch import MonkeyPatch

    from loaded_dicewriter.settings import get_settings

    mp = monkeypatch if isinstance(monkeypatch, MonkeyPatch) else MonkeyPatch()
    clear_settings_cache()
    mp.setenv("APP_BASE_PATH", "/loaded-dicewriter/")
    clear_settings_cache()
    try:
        s = get_settings()
        assert s.app_base_path == "/loaded-dicewriter/"
        assert s.normalized_app_base_path == "/loaded-dicewriter/"
    finally:
        clear_settings_cache()
