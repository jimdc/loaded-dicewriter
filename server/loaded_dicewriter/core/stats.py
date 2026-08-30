"""Detector statistics: z-score and one-sided normal survival p-value."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal


def normal_sf(z: float) -> float:
    """One-sided standard normal survival function P(Z > z).

    Implemented with math.erfc so CI has no SciPy dependency.
    """
    if math.isnan(z):
        return float("nan")
    # Clamp extreme tails for numerical stability of display.
    if z > 40.0:
        return 0.0
    if z < -40.0:
        return 1.0
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def z_score(*, green_count: int, scored_count: int, gamma: float) -> float:
    """Kirchenbauer et al. one-proportion z against expected green rate γ."""
    t = scored_count
    if t <= 0:
        return 0.0
    if not (0.0 < gamma < 1.0):
        return 0.0
    expected = gamma * t
    variance = t * gamma * (1.0 - gamma)
    if variance <= 0.0:
        return 0.0
    return (green_count - expected) / math.sqrt(variance)


Verdict = Literal[
    "insufficient_scored_tokens",
    "no_evidence",
    "detected",
]


@dataclass(frozen=True)
class DetectionResult:
    num_tokens_total: int
    num_tokens_scored: int
    num_green: int
    expected_green: float
    green_fraction: float | None
    z_score: float
    p_value: float
    detected: bool
    threshold: float
    excluded_prefix_count: int
    excluded_repeated_count: int
    excluded_other_count: int
    verdict: Verdict
    verdict_label: str

    def as_dict(self) -> dict[str, object]:
        return {
            "num_tokens_total": self.num_tokens_total,
            "num_tokens_scored": self.num_tokens_scored,
            "num_green": self.num_green,
            "expected_green": self.expected_green,
            "green_fraction": self.green_fraction,
            "z_score": self.z_score,
            "p_value": self.p_value,
            "detected": self.detected,
            "threshold": self.threshold,
            "excluded_prefix_count": self.excluded_prefix_count,
            "excluded_repeated_count": self.excluded_repeated_count,
            "excluded_other_count": self.excluded_other_count,
            "verdict": self.verdict,
            "verdict_label": self.verdict_label,
        }


def compute_detection(
    *,
    num_tokens_total: int,
    num_tokens_scored: int,
    num_green: int,
    gamma: float,
    threshold: float,
    min_scored_tokens: int = 20,
    excluded_prefix_count: int = 0,
    excluded_repeated_count: int = 0,
    excluded_other_count: int = 0,
) -> DetectionResult:
    """Aggregate portable detection stats with honest UX verdicts."""
    t = max(0, num_tokens_scored)
    k = max(0, num_green)
    if t > 0:
        k = min(k, t)
    expected = gamma * t if t > 0 else 0.0
    z = z_score(green_count=k, scored_count=t, gamma=gamma)
    p = normal_sf(z) if t > 0 else 1.0
    green_fraction = (k / t) if t > 0 else None
    detected = t >= min_scored_tokens and z >= threshold

    if t < min_scored_tokens:
        verdict: Verdict = "insufficient_scored_tokens"
        verdict_label = "insufficient scored tokens"
    elif detected:
        verdict = "detected"
        verdict_label = f"detected at threshold z ≥ {threshold:g}"
    else:
        verdict = "no_evidence"
        verdict_label = "no evidence under this key/configuration"

    return DetectionResult(
        num_tokens_total=num_tokens_total,
        num_tokens_scored=t,
        num_green=k,
        expected_green=expected,
        green_fraction=green_fraction,
        z_score=z,
        p_value=p,
        detected=detected,
        threshold=threshold,
        excluded_prefix_count=excluded_prefix_count,
        excluded_repeated_count=excluded_repeated_count,
        excluded_other_count=excluded_other_count,
        verdict=verdict,
        verdict_label=verdict_label,
    )
