"""Toy loaded-dice engine: real token-by-token sampling over a fixed vocabulary.

No GPU, no model files, no network. A keyed green-list watermark (γ, δ, h, key)
genuinely biases a pseudorandom token subset at each step.
"""

from __future__ import annotations

import math
import random
import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from loaded_dicewriter.core.keys import TEACHING_KEY, key_fingerprint
from loaded_dicewriter.core.profiles import TEACHING_KGW, WatermarkProfile
from loaded_dicewriter.core.stats import compute_detection, normal_sf, z_score
from loaded_dicewriter.core.types import BranchResult, CandidateProb, TokenTrace
from loaded_dicewriter.generation.sampler import (
    entropy_bits,
    sample_categorical_u,
    softmax,
    top_k_candidates,
)
from loaded_dicewriter.watermark.kgw_inspectable import InspectableKGW

# Small fixed vocabulary for deterministic toy sentences (no external resources).
TOY_VOCAB: tuple[str, ...] = (
    "the",
    "city",
    "grows",
    "small",
    "shops",
    "because",
    "people",
    "need",
    "nearby",
    "goods",
    "and",
    "quiet",
    "streets",
    "invite",
    "walking",
    "trade",
    "patterns",
    "form",
    "over",
    "time",
    "local",
    "markets",
    "offer",
    "choice",
    "while",
    "dense",
    "blocks",
    "keep",
    "daily",
    "errands",
    "short",
    "so",
    "neighbors",
    "meet",
    "often",
    "around",
    "corner",
    "stores",
    "that",
    "serve",
)


@dataclass(frozen=True)
class FakeToken:
    """Backward-compatible token summary for older tests/status probes."""

    position: int
    text: str
    token_id: int


@dataclass(frozen=True)
class FakeBranch:
    label: str
    text: str
    tokens: list[FakeToken]


@dataclass(frozen=True)
class FakeGenerationResult:
    prompt: str
    seed: int
    control: FakeBranch
    loaded: FakeBranch


@dataclass
class StepEvent:
    """One sampled token on one branch (for streaming adapters)."""

    branch: str
    position: int
    token: TokenTrace
    text_so_far: str
    detection: dict[str, Any]
    finished: bool


class FakeEngine:
    """Produces control/loaded pairs via real categorical sampling + KGW bias."""

    def __init__(
        self,
        default_length: int = 48,
        *,
        key: bytes | None = None,
        profile: WatermarkProfile | None = None,
        temperature: float = 1.0,
        top_k_trace: int = 6,
    ) -> None:
        self.default_length = default_length
        self.key = key if key is not None else TEACHING_KEY
        self.profile = profile or TEACHING_KGW
        self.temperature = temperature
        self.top_k_trace = top_k_trace
        self.vocab = TOY_VOCAB
        self.vocab_size = len(TOY_VOCAB)
        self.watermark = InspectableKGW(key=self.key, profile=self.profile)
        # Zipf-like base preference: earlier words slightly more common.
        self._base_logits = [-math.log(i + 1.5) for i in range(self.vocab_size)]

    @property
    def key_fp(self) -> str:
        return key_fingerprint(self.key)

    def generate_pair(
        self,
        prompt: str,
        *,
        seed: int = 0,
        length: int | None = None,
    ) -> FakeGenerationResult:
        """Legacy compact result used by status probes and early tests."""
        full = self.generate_pair_traced(prompt, seed=seed, length=length)
        return FakeGenerationResult(
            prompt=prompt,
            seed=seed,
            control=self._to_fake_branch(full["control"]),
            loaded=self._to_fake_branch(full["loaded"]),
        )

    def generate_pair_traced(
        self,
        prompt: str,
        *,
        seed: int = 0,
        length: int | None = None,
        apply_watermark_to_loaded: bool = True,
    ) -> dict[str, BranchResult]:
        """Path-coupled clean/loaded pair via common random numbers.

        One shared base distribution per step (context = loaded path so far).
        Clean samples base; loaded samples biased with the same uniform draw.
        """
        n = length if length is not None else self.default_length
        shared_rng = random.Random(int(seed) & 0x7FFF_FFFF_FFFF_FFFF)
        control_state = self._BranchState("control", apply_watermark=False)
        loaded_state = self._BranchState(
            "loaded", apply_watermark=apply_watermark_to_loaded
        )
        for _ in range(n):
            u = shared_rng.random()
            # Shared generation context = watermarked path (path-coupled CRN).
            gen_context = list(loaded_state.token_ids)
            self._step(control_state, prompt, u=u, gen_context_ids=gen_context)
            self._step(loaded_state, prompt, u=u, gen_context_ids=gen_context)
        return {
            "control": self._branch_result(control_state),
            "loaded": self._branch_result(loaded_state),
        }

    def iter_pair_steps(
        self,
        prompt: str,
        *,
        seed: int = 0,
        length: int | None = None,
        stop_flag: list[bool] | None = None,
    ) -> Iterator[StepEvent]:
        """Interleave control/loaded steps for streaming (control then loaded each pos).

        Path-coupled CRN: shared base logits from the loaded prefix; same uniform
        draw for both branches so they differ only where watermark bias flips.
        """
        n = length if length is not None else self.default_length
        shared_rng = random.Random(int(seed) & 0x7FFF_FFFF_FFFF_FFFF)
        ctrl_state = self._BranchState("control", apply_watermark=False)
        load_state = self._BranchState("loaded", apply_watermark=True)

        for pos in range(n):
            if stop_flag and stop_flag[0]:
                break
            u = shared_rng.random()
            gen_context = list(load_state.token_ids)
            for state in (ctrl_state, load_state):
                if stop_flag and stop_flag[0]:
                    break
                event = self._step(state, prompt, u=u, gen_context_ids=gen_context)
                is_last = pos == n - 1
                if is_last and not (stop_flag and stop_flag[0]):
                    event.finished = True
                yield event

    def _branch_result(self, state: FakeEngine._BranchState) -> BranchResult:
        detection = self._running_detection(state.token_ids, state.tokens)
        return BranchResult(
            label=state.label,  # type: ignore[arg-type]
            text=state.text,
            token_ids=list(state.token_ids),
            tokens=list(state.tokens),
            detection=detection,
        )

    class _BranchState:
        def __init__(self, label: str, *, apply_watermark: bool) -> None:
            self.label = label
            self.apply_watermark = apply_watermark
            self.token_ids: list[int] = []
            self.tokens: list[TokenTrace] = []
            self.words: list[str] = []
            self.finished = False

        @property
        def text(self) -> str:
            if not self.words:
                return ""
            body = " ".join(self.words)
            return body[0].upper() + body[1:] + "."

    def _step(
        self,
        state: FakeEngine._BranchState,
        prompt: str,
        *,
        u: float,
        gen_context_ids: list[int] | None = None,
    ) -> StepEvent:
        t0 = time.perf_counter()
        position = len(state.token_ids)
        # Path-coupled CRN: base distribution from the shared generation context
        # (loaded path). Portable detection still scores this branch's own tokens.
        gen_context = (
            list(gen_context_ids) if gen_context_ids is not None else list(state.token_ids)
        )
        base_logits = self._position_logits(prompt, gen_context)

        favored_mask = self.watermark.favored_mask(
            context_ids=gen_context,
            vocab_size=self.vocab_size,
        )
        base_probs = softmax(base_logits, temperature=self.temperature)

        if state.apply_watermark:
            bias = self.watermark.bias_logits(context_ids=gen_context, logits=base_logits)
            biased_logits = bias.logits_after
            sample_probs = softmax(biased_logits, temperature=self.temperature)
        else:
            biased_logits = list(base_logits)
            sample_probs = list(base_probs)

        # Shared uniform u: only green-list bias can change which token wins.
        token_id = sample_categorical_u(sample_probs, u)
        word = self.vocab[token_id]
        favored = favored_mask[token_id]

        # Portable detector bookkeeping uses completion-internal context only.
        h = self.profile.context_width
        eligible = position >= h
        exclusion_reason = None
        unit: tuple[tuple[int, ...], int] | None = None
        branch_context = list(state.token_ids)
        if not eligible:
            exclusion_reason = "missing_context"
        else:
            ctx = branch_context[-h:] if h > 0 else []
            unit = (tuple(ctx), token_id)
            if self.profile.ignore_repeated_ngrams:
                prior_units = {
                    (tuple(state.token_ids[max(0, i - h) : i]), state.token_ids[i])
                    for i in range(h, position)
                }
                if unit in prior_units:
                    eligible = False
                    exclusion_reason = "repeated_ngram"

        # Running green/scored counts after this token.
        prev_scored = state.tokens[-1].scored_count_after if state.tokens else 0
        prev_green = state.tokens[-1].green_count_after if state.tokens else 0
        scored_after = prev_scored
        green_after = prev_green
        if eligible:
            scored_after += 1
            # Recompute favored under portable context window for detection.
            portable_ctx = branch_context[-h:] if h > 0 else []
            portable_favored = self.watermark.is_token_green(
                token_id, context_ids=portable_ctx
            )
            favored = portable_favored
            if portable_favored:
                green_after += 1

        z_after = z_score(
            green_count=green_after,
            scored_count=scored_after,
            gamma=self.profile.gamma,
        )
        p_after = normal_sf(z_after) if scored_after > 0 else 1.0

        before_rows = top_k_candidates(
            base_probs,
            texts=self.vocab,
            favored_mask=favored_mask,
            k=self.top_k_trace,
            always_include=token_id,
        )
        after_probs = sample_probs if state.apply_watermark else base_probs
        after_rows = top_k_candidates(
            after_probs,
            texts=self.vocab,
            favored_mask=favored_mask,
            k=self.top_k_trace,
            always_include=token_id,
        )

        biased_prob = float(sample_probs[token_id]) if state.apply_watermark else None
        biased_logit = float(biased_logits[token_id]) if state.apply_watermark else None

        trace = TokenTrace(
            position=position,
            token_id=token_id,
            text=word,
            context_ids=list(gen_context[-h:] if h > 0 else []),
            favored=bool(favored),
            eligible=eligible,
            exclusion_reason=exclusion_reason,  # type: ignore[arg-type]
            base_logit=float(base_logits[token_id]),
            biased_logit=biased_logit,
            base_probability=float(base_probs[token_id]),
            biased_probability=biased_prob,
            final_sampling_probability=float(sample_probs[token_id]),
            entropy=entropy_bits(base_probs),
            green_count_after=green_after,
            scored_count_after=scored_after,
            z_score_after=z_after,
            p_value_after=p_after,
            top_candidates_before=[
                CandidateProb(tid, txt, prob, fav) for tid, txt, prob, fav in before_rows
            ],
            top_candidates_after=[
                CandidateProb(tid, txt, prob, fav) for tid, txt, prob, fav in after_rows
            ],
            latency_ms=(time.perf_counter() - t0) * 1000.0,
        )

        state.token_ids.append(token_id)
        state.tokens.append(trace)
        state.words.append(word)

        detection = self._running_detection(state.token_ids, state.tokens)
        return StepEvent(
            branch=state.label,
            position=position,
            token=trace,
            text_so_far=state.text,
            detection=detection,
            finished=False,
        )

    def _position_logits(
        self,
        prompt: str,
        context_ids: list[int],
    ) -> list[float]:
        """Slightly position- and prompt-dependent base logits (still a toy LM).

        Fully deterministic in (prompt, context) so CRN coupling works: identical
        histories ⇒ identical base distributions; only watermark bias can flip.
        """
        # Prompt hash nudges a few "topic" tokens upward without network/models.
        prompt_nudge = sum(ord(c) for c in prompt[:64]) % self.vocab_size
        logits = list(self._base_logits)
        logits[prompt_nudge] += 0.6
        logits[(prompt_nudge + 3) % self.vocab_size] += 0.35
        if context_ids:
            prev = context_ids[-1]
            # Mild bigram preference: next index slightly favored.
            logits[(prev + 1) % self.vocab_size] += 0.45
            logits[(prev + 5) % self.vocab_size] += 0.2
            # Small deterministic context hash for variety (not a sampling draw).
            mix = (prev * 2654435761 + len(context_ids) * 97) & 0xFFFFFFFF
            for i in range(self.vocab_size):
                logits[i] += (((mix >> (i % 16)) & 1) * 2 - 1) * 0.03
        return logits

    def _running_detection(
        self,
        token_ids: list[int],
        tokens: list[TokenTrace],
    ) -> dict[str, Any]:
        if tokens:
            scored = tokens[-1].scored_count_after
            green = tokens[-1].green_count_after
            excl_prefix = sum(
                1 for t in tokens if t.exclusion_reason == "missing_context"
            )
            excl_repeated = sum(
                1 for t in tokens if t.exclusion_reason == "repeated_ngram"
            )
        else:
            scored = 0
            green = 0
            excl_prefix = 0
            excl_repeated = 0
        result = compute_detection(
            num_tokens_total=len(token_ids),
            num_tokens_scored=scored,
            num_green=green,
            gamma=self.profile.gamma,
            threshold=self.profile.z_threshold,
            min_scored_tokens=self.profile.min_scored_tokens,
            excluded_prefix_count=excl_prefix,
            excluded_repeated_count=excl_repeated,
        )
        return result.as_dict()

    def _to_fake_branch(self, branch: BranchResult) -> FakeBranch:
        return FakeBranch(
            label=branch.label,
            text=branch.text,
            tokens=[
                FakeToken(position=t.position, text=t.text, token_id=t.token_id)
                for t in branch.tokens
            ],
        )

    def _empty_token(self) -> TokenTrace:
        return TokenTrace(
            position=0,
            token_id=0,
            text="",
            context_ids=[],
            favored=False,
            eligible=False,
            exclusion_reason="missing_context",
            base_logit=0.0,
            biased_logit=None,
            base_probability=0.0,
            biased_probability=None,
            final_sampling_probability=0.0,
            entropy=0.0,
            green_count_after=0,
            scored_count_after=0,
            z_score_after=0.0,
            p_value_after=1.0,
        )
