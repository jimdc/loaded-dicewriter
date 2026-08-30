"""Keyed pseudorandom green-list membership (simple context-seeded KGW)."""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Sequence

from loaded_dicewriter.core.keys import pack_context


def _membership_u01(key: bytes, context_ids: Sequence[int], token_id: int) -> float:
    """Uniform [0, 1) value for (key, context, token) via HMAC-SHA256."""
    msg = pack_context(tuple(context_ids)) + (int(token_id) & 0xFFFFFFFF).to_bytes(4, "big")
    digest = hmac.new(key, msg, hashlib.sha256).digest()
    return int.from_bytes(digest[:8], "big") / float(1 << 64)


def is_green(
    token_id: int,
    *,
    context_ids: Sequence[int],
    key: bytes,
    gamma: float,
) -> bool:
    """Return True if token_id is in the favored (green) set for this context."""
    if gamma <= 0.0:
        return False
    if gamma >= 1.0:
        return True
    return _membership_u01(key, context_ids, token_id) < gamma


def green_mask(
    *,
    context_ids: Sequence[int],
    vocab_size: int,
    key: bytes,
    gamma: float,
) -> list[bool]:
    """Boolean mask over the vocabulary: True = favored/green.

    Optimized: one HMAC template over the context, then ``copy()+update`` per
    token id (much faster than ``hmac.new`` per token).
    """
    if vocab_size < 0:
        raise ValueError("vocab_size must be non-negative")
    if gamma <= 0.0:
        return [False] * vocab_size
    if gamma >= 1.0:
        return [True] * vocab_size
    ctx = pack_context(tuple(context_ids))
    template = hmac.new(key, ctx, hashlib.sha256)
    scale = float(1 << 64)
    out = [False] * vocab_size
    for i in range(vocab_size):
        h = template.copy()
        h.update((int(i) & 0xFFFFFFFF).to_bytes(4, "big"))
        u01 = int.from_bytes(h.digest()[:8], "big") / scale
        if u01 < gamma:
            out[i] = True
    return out


def green_ids_for_candidates(
    token_ids: Sequence[int],
    *,
    context_ids: Sequence[int],
    key: bytes,
    gamma: float,
) -> set[int]:
    """Green membership for a small candidate set (fast path for sampling)."""
    return {
        int(t)
        for t in token_ids
        if is_green(int(t), context_ids=context_ids, key=key, gamma=gamma)
    }


def green_token_ids(
    *,
    context_ids: Sequence[int],
    vocab_size: int,
    key: bytes,
    gamma: float,
) -> list[int]:
    """List of favored token ids for this context (for inspection/tests)."""
    mask = green_mask(
        context_ids=context_ids,
        vocab_size=vocab_size,
        key=key,
        gamma=gamma,
    )
    return [i for i, g in enumerate(mask) if g]
