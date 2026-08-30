"""Inspectable Kirchenbauer green-list watermark (Teaching KGW profile)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from loaded_dicewriter.core.prf import green_mask, is_green
from loaded_dicewriter.core.profiles import TEACHING_KGW, WatermarkProfile
from loaded_dicewriter.core.stats import DetectionResult, compute_detection
from loaded_dicewriter.watermark.base import BiasResult


@dataclass
class PositionScore:
    position: int
    token_id: int
    context_ids: list[int]
    favored: bool
    eligible: bool
    exclusion_reason: str | None


@dataclass
class DetectionTrace:
    result: DetectionResult
    positions: list[PositionScore]


class InspectableKGW:
    """Keyed green-list watermark with portable detection and n-gram exclusion."""

    def __init__(
        self,
        *,
        key: bytes,
        profile: WatermarkProfile | None = None,
    ) -> None:
        self.key = key
        self.profile = profile or TEACHING_KGW
        self.profile_id = self.profile.id

    def favored_mask(
        self,
        *,
        context_ids: Sequence[int],
        vocab_size: int,
    ) -> list[bool]:
        ctx = self._context_window(context_ids)
        return green_mask(
            context_ids=ctx,
            vocab_size=vocab_size,
            key=self.key,
            gamma=self.profile.gamma,
        )

    def bias_logits(
        self,
        *,
        context_ids: Sequence[int],
        logits: Sequence[float],
    ) -> BiasResult:
        mask = self.favored_mask(context_ids=context_ids, vocab_size=len(logits))
        delta = self.profile.delta
        after = [logit + (delta if fav else 0.0) for logit, fav in zip(logits, mask, strict=True)]
        return BiasResult(logits_after=after, favored_mask=mask, delta=delta)

    def is_token_green(
        self,
        token_id: int,
        *,
        context_ids: Sequence[int],
    ) -> bool:
        ctx = self._context_window(context_ids)
        return is_green(
            token_id,
            context_ids=ctx,
            key=self.key,
            gamma=self.profile.gamma,
        )

    def score_tokens(
        self,
        *,
        token_ids: Sequence[int],
        portable: bool = True,
    ) -> DetectionResult:
        trace = self.score_trace(token_ids=token_ids, portable=portable)
        return trace.result

    def score_trace(
        self,
        *,
        token_ids: Sequence[int],
        portable: bool = True,
    ) -> DetectionTrace:
        """Portable detection: score completion-only text with h-prefix exclusion.

        When portable=True (default), the first ``context_width`` tokens lack a full
        completion-internal context and are labeled ``missing_context``.
        """
        h = self.profile.context_width
        ids = list(token_ids)
        positions: list[PositionScore] = []
        green = 0
        scored = 0
        excl_prefix = 0
        excl_repeated = 0
        excl_other = 0
        seen_units: set[tuple[tuple[int, ...], int]] = set()

        for pos, tok in enumerate(ids):
            if portable and pos < h:
                positions.append(
                    PositionScore(
                        position=pos,
                        token_id=tok,
                        context_ids=[],
                        favored=False,
                        eligible=False,
                        exclusion_reason="missing_context",
                    )
                )
                excl_prefix += 1
                continue

            # Context is prior completion tokens only (portable).
            start = max(0, pos - h)
            ctx = ids[start:pos]
            # If we somehow lack h tokens of context (non-portable edge), skip.
            if len(ctx) < h:
                positions.append(
                    PositionScore(
                        position=pos,
                        token_id=tok,
                        context_ids=list(ctx),
                        favored=False,
                        eligible=False,
                        exclusion_reason="missing_context",
                    )
                )
                excl_prefix += 1
                continue

            unit = (tuple(ctx), tok)
            if self.profile.ignore_repeated_ngrams and unit in seen_units:
                positions.append(
                    PositionScore(
                        position=pos,
                        token_id=tok,
                        context_ids=list(ctx),
                        favored=False,
                        eligible=False,
                        exclusion_reason="repeated_ngram",
                    )
                )
                excl_repeated += 1
                continue

            seen_units.add(unit)
            favored = self.is_token_green(tok, context_ids=ctx)
            if favored:
                green += 1
            scored += 1
            positions.append(
                PositionScore(
                    position=pos,
                    token_id=tok,
                    context_ids=list(ctx),
                    favored=favored,
                    eligible=True,
                    exclusion_reason=None,
                )
            )

        result = compute_detection(
            num_tokens_total=len(ids),
            num_tokens_scored=scored,
            num_green=green,
            gamma=self.profile.gamma,
            threshold=self.profile.z_threshold,
            min_scored_tokens=self.profile.min_scored_tokens,
            excluded_prefix_count=excl_prefix,
            excluded_repeated_count=excl_repeated,
            excluded_other_count=excl_other,
        )
        return DetectionTrace(result=result, positions=positions)

    def _context_window(self, context_ids: Sequence[int]) -> list[int]:
        h = self.profile.context_width
        if h <= 0:
            return []
        ids = list(context_ids)
        if len(ids) <= h:
            return ids
        return ids[-h:]
