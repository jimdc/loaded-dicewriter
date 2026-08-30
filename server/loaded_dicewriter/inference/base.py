"""Narrow inference backend protocol."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ModelInfo:
    id: str
    backend: str
    revision: str | None
    device: str
    vocab_size: int | None = None


class InferenceBackend(Protocol):
    model_info: ModelInfo

    async def load(self) -> None: ...

    async def unload(self) -> None: ...
