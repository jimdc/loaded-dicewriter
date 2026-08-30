"""Seeded categorical sampling utilities over logit vectors."""

from __future__ import annotations

import math
import random
from collections.abc import Sequence


def softmax(logits: Sequence[float], *, temperature: float = 1.0) -> list[float]:
    if not logits:
        return []
    t = temperature if temperature > 0.0 else 1.0
    scaled = [x / t for x in logits]
    m = max(scaled)
    exps = [math.exp(x - m) for x in scaled]
    total = sum(exps)
    if total <= 0.0:
        n = len(logits)
        return [1.0 / n] * n
    return [e / total for e in exps]


def entropy_bits(probs: Sequence[float]) -> float:
    h = 0.0
    for p in probs:
        if p > 0.0:
            h -= p * math.log2(p)
    return h


def sample_categorical_u(probs: Sequence[float], u: float) -> int:
    """Inverse-CDF sample using a pre-drawn uniform ``u`` in [0, 1).

    Used for common-random-number coupling: clean and loaded branches draw once
    and apply the same ``u`` to base vs green-list-biased distributions so they
    stay identical except where the bias changes which token wins.
    """
    if not probs:
        raise ValueError("empty probability vector")
    # Clamp for numerical edge cases (u==1.0 from float noise).
    r = 0.0 if u < 0.0 else (0.999999999999 if u >= 1.0 else float(u))
    cumulative = 0.0
    last = len(probs) - 1
    for i, p in enumerate(probs):
        cumulative += p
        if r <= cumulative or i == last:
            return i
    return last


def sample_categorical(probs: Sequence[float], rng: random.Random) -> int:
    if not probs:
        raise ValueError("empty probability vector")
    return sample_categorical_u(probs, rng.random())


def top_k_candidates(
    probs: Sequence[float],
    *,
    texts: Sequence[str],
    favored_mask: Sequence[bool],
    k: int = 6,
    always_include: int | None = None,
) -> list[tuple[int, str, float, bool]]:
    """Return up to k (token_id, text, prob, favored) rows for the inspector."""
    order = sorted(range(len(probs)), key=lambda i: probs[i], reverse=True)
    chosen: list[int] = []
    if always_include is not None and 0 <= always_include < len(probs):
        chosen.append(always_include)
    for i in order:
        if i not in chosen:
            chosen.append(i)
        if len(chosen) >= k:
            break
    return [
        (i, texts[i] if i < len(texts) else str(i), float(probs[i]), bool(favored_mask[i]))
        for i in chosen
    ]
