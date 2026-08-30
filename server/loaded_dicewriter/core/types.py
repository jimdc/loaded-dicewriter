"""Shared generation / detection value types."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

BranchLabel = Literal["control", "loaded"]
ExclusionReason = Literal[
    "missing_context",
    "repeated_ngram",
    "special_token",
]


@dataclass(frozen=True)
class CandidateProb:
    token_id: int
    text: str
    probability: float
    favored: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TokenTrace:
    position: int
    token_id: int
    text: str
    context_ids: list[int]
    favored: bool
    eligible: bool
    exclusion_reason: ExclusionReason | None
    base_logit: float
    biased_logit: float | None
    base_probability: float
    biased_probability: float | None
    final_sampling_probability: float
    entropy: float
    green_count_after: int
    scored_count_after: int
    z_score_after: float
    p_value_after: float
    top_candidates_before: list[CandidateProb] = field(default_factory=list)
    top_candidates_after: list[CandidateProb] = field(default_factory=list)
    latency_ms: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "position": self.position,
            "token_id": self.token_id,
            "text": self.text,
            "context_ids": list(self.context_ids),
            "favored": self.favored,
            "eligible": self.eligible,
            "exclusion_reason": self.exclusion_reason,
            "base_logit": self.base_logit,
            "biased_logit": self.biased_logit,
            "base_probability": self.base_probability,
            "biased_probability": self.biased_probability,
            "final_sampling_probability": self.final_sampling_probability,
            "entropy": self.entropy,
            "green_count_after": self.green_count_after,
            "scored_count_after": self.scored_count_after,
            "z_score_after": self.z_score_after,
            "p_value_after": self.p_value_after,
            "top_candidates_before": [c.as_dict() for c in self.top_candidates_before],
            "top_candidates_after": [c.as_dict() for c in self.top_candidates_after],
            "latency_ms": self.latency_ms,
        }


@dataclass
class BranchResult:
    label: BranchLabel
    text: str
    token_ids: list[int]
    tokens: list[TokenTrace]
    detection: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "text": self.text,
            "token_ids": list(self.token_ids),
            "tokens": [t.as_dict() for t in self.tokens],
            "detection": dict(self.detection),
        }
