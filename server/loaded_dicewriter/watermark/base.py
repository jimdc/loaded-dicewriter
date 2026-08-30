"""Watermark algorithm protocol."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from loaded_dicewriter.core.stats import DetectionResult


@dataclass(frozen=True)
class BiasResult:
    logits_after: list[float]
    favored_mask: list[bool]
    delta: float


class WatermarkAlgorithm(Protocol):
    profile_id: str

    def favored_mask(
        self,
        *,
        context_ids: Sequence[int],
        vocab_size: int,
    ) -> list[bool]: ...

    def bias_logits(
        self,
        *,
        context_ids: Sequence[int],
        logits: Sequence[float],
    ) -> BiasResult: ...

    def score_tokens(
        self,
        *,
        token_ids: Sequence[int],
        portable: bool = True,
    ) -> DetectionResult: ...
