"""Named watermark profiles. Teaching KGW is the default for the first release."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WatermarkProfile:
    id: str
    name: str
    gamma: float
    delta: float
    context_width: int
    ignore_repeated_ngrams: bool
    z_threshold: float
    min_scored_tokens: int = 20

    def fingerprint_summary(self, key_fp: str) -> str:
        return (
            f"{self.name} · γ {self.gamma:g} · δ {self.delta:g} · "
            f"h {self.context_width} · key {key_fp}…"
        )


TEACHING_KGW = WatermarkProfile(
    id="teaching-kgw",
    name="Teaching KGW",
    gamma=0.25,
    delta=2.0,
    context_width=1,
    ignore_repeated_ngrams=True,
    z_threshold=4.0,
    min_scored_tokens=20,
)

PROFILES: dict[str, WatermarkProfile] = {
    TEACHING_KGW.id: TEACHING_KGW,
}


def get_profile(profile_id: str | None = None) -> WatermarkProfile:
    if profile_id is None or profile_id not in PROFILES:
        return TEACHING_KGW
    return PROFILES[profile_id]
