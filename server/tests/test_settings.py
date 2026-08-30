"""Config loader guardrails."""

from __future__ import annotations

from loaded_dicewriter.settings import clear_settings_cache, get_settings


def test_default_loopback_and_no_telemetry() -> None:
    clear_settings_cache()
    settings = get_settings()
    assert settings.server.host == "127.0.0.1"
    assert settings.server.port == 8765
    assert settings.privacy.telemetry is False
    assert settings.model.mode == "fake"
    assert settings.model_ready is True
    assert settings.app_ready is True


def test_env_port_override(monkeypatch: object) -> None:
    from _pytest.monkeypatch import MonkeyPatch

    mp = monkeypatch if isinstance(monkeypatch, MonkeyPatch) else MonkeyPatch()
    clear_settings_cache()
    mp.setenv("LDW_PORT", "9999")
    mp.setenv("LDW_MODEL_MODE", "fake")
    clear_settings_cache()
    try:
        s = get_settings()
        assert s.server.port == 9999
        assert s.model.mode == "fake"
    finally:
        clear_settings_cache()
