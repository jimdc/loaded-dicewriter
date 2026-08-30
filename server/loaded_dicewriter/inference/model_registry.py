"""Model registry loaded from config/models.toml (optional file)."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from loaded_dicewriter.settings import REPO_ROOT


@dataclass(frozen=True)
class ModelSpec:
    id: str
    hf_id: str
    revision: str | None
    backend: str
    dtype: str
    chat_template: bool
    max_context_tokens: int
    recommended_max_new_tokens: int
    local_path: str | None = None


def _default_specs() -> list[ModelSpec]:
    return [
        ModelSpec(
            id="local-instruct-small",
            hf_id="sshleifer/tiny-gpt2",
            revision=None,
            backend="transformers",
            dtype="auto",
            chat_template=False,
            max_context_tokens=1024,
            recommended_max_new_tokens=64,
            local_path=None,
        )
    ]


def load_model_registry(path: Path | None = None) -> list[ModelSpec]:
    candidate = path or (REPO_ROOT / "config" / "models.toml")
    if not candidate.is_file():
        return _default_specs()
    with candidate.open("rb") as fh:
        raw: dict[str, Any] = tomllib.load(fh)
    models = raw.get("models") or []
    out: list[ModelSpec] = []
    for m in models:
        out.append(
            ModelSpec(
                id=str(m["id"]),
                hf_id=str(m["hf_id"]),
                revision=m.get("revision"),
                backend=str(m.get("backend", "transformers")),
                dtype=str(m.get("dtype", "auto")),
                chat_template=bool(m.get("chat_template", True)),
                max_context_tokens=int(m.get("max_context_tokens", 4096)),
                recommended_max_new_tokens=int(m.get("recommended_max_new_tokens", 160)),
                local_path=m.get("local_path") or m.get("model_path"),
            )
        )
    return out or _default_specs()


def get_model_spec(model_id: str | None = None) -> ModelSpec:
    specs = load_model_registry()
    if model_id:
        for s in specs:
            if s.id == model_id:
                return s
    return specs[0]
