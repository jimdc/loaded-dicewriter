"""Environment and config loader. Loopback by default; no telemetry."""

from __future__ import annotations

import os
import tomllib
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from loaded_dicewriter import __version__

REPO_ROOT = Path(__file__).resolve().parents[2]


class ServerSettings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8765
    data_dir: Path = Field(default=REPO_ROOT / "data")


class ModelSettings(BaseModel):
    mode: Literal["fake", "transformers"] = "fake"
    model_path: str | None = None


class PrivacySettings(BaseModel):
    telemetry: bool = False


def normalize_app_base_path(raw: str | None) -> str:
    """Normalize APP_BASE_PATH to `/` or `/slug/` (leading + trailing slash)."""
    if raw is None:
        return "/"
    value = raw.strip()
    if not value or value == "/":
        return "/"
    with_leading = value if value.startswith("/") else f"/{value}"
    return with_leading if with_leading.endswith("/") else f"{with_leading}/"


def app_base_prefix(raw: str | None) -> str:
    """Prefix without trailing slash for path matching, or empty at root."""
    base = normalize_app_base_path(raw)
    if base == "/":
        return ""
    return base.rstrip("/")


class Settings(BaseModel):
    server: ServerSettings = Field(default_factory=ServerSettings)
    model: ModelSettings = Field(default_factory=ModelSettings)
    privacy: PrivacySettings = Field(default_factory=PrivacySettings)
    app_base_path: str = "/"
    version: str = __version__

    @property
    def model_ready(self) -> bool:
        """Fake mode is always ready; real models require a local path later."""
        if self.model.mode == "fake":
            return True
        if not self.model.model_path:
            return False
        return Path(self.model.model_path).exists()

    @property
    def app_ready(self) -> bool:
        """Process + config are loadable (independent of model readiness)."""
        return not self.privacy.telemetry  # telemetry must stay off

    @property
    def normalized_app_base_path(self) -> str:
        return normalize_app_base_path(self.app_base_path)


def _load_toml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with path.open("rb") as fh:
        return tomllib.load(fh)


def _resolve_config_path() -> Path | None:
    env = os.environ.get("LDW_CONFIG")
    if env:
        return Path(env)
    candidate = REPO_ROOT / "config" / "app.toml"
    if candidate.is_file():
        return candidate
    example = REPO_ROOT / "config" / "app.example.toml"
    if example.is_file():
        return example
    return None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    path = _resolve_config_path()
    raw: dict[str, Any] = _load_toml(path) if path else {}

    server_raw = dict(raw.get("server", {}))
    if "data_dir" in server_raw and not Path(server_raw["data_dir"]).is_absolute():
        server_raw["data_dir"] = str(REPO_ROOT / server_raw["data_dir"])

    # Environment overrides (loopback guardrails)
    host = os.environ.get("LDW_HOST") or str(server_raw.get("host", "127.0.0.1"))
    port_raw = os.environ.get("LDW_PORT") or str(server_raw.get("port", 8765))
    port = int(port_raw)
    mode_raw = os.environ.get("LDW_MODEL_MODE") or str(raw.get("model", {}).get("mode", "fake"))
    mode: Literal["fake", "transformers"]
    if mode_raw == "transformers":
        mode = "transformers"
    else:
        mode = "fake"

    server = ServerSettings(
        host=host,
        port=port,
        data_dir=Path(server_raw.get("data_dir", REPO_ROOT / "data")),
    )
    model = ModelSettings(
        mode=mode,
        model_path=raw.get("model", {}).get("model_path"),
    )
    privacy = PrivacySettings(
        telemetry=bool(raw.get("privacy", {}).get("telemetry", False)),
    )
    if privacy.telemetry:
        # Hard guardrail: refuse telemetry config.
        privacy = PrivacySettings(telemetry=False)

    # APP_BASE_PATH: hub subpath (runtime middleware). Empty/`/` = root.
    # Must match the frontend build-time APP_BASE_PATH for asset/API URLs.
    base_raw = os.environ.get("APP_BASE_PATH")
    if base_raw is None:
        base_raw = str(raw.get("server", {}).get("app_base_path", "/"))
    app_base_path = normalize_app_base_path(base_raw)

    return Settings(
        server=server,
        model=model,
        privacy=privacy,
        app_base_path=app_base_path,
        version=__version__,
    )


def clear_settings_cache() -> None:
    get_settings.cache_clear()
