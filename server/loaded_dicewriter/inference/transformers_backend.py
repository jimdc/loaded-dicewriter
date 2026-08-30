"""Hugging Face Transformers backend for real local models (LDW-004/005).

Default product mode remains ``fake`` so CI and the hosted loopback service never
download weights. This module is code-complete against the transformers API and
unit-tested for the KGW path via a lightweight logits stub; live weight loading
is only exercised when ``model.mode = transformers`` and a local path exists.
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import AsyncIterator, Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from loaded_dicewriter.core.prf import green_ids_for_candidates, is_green
from loaded_dicewriter.core.profiles import WatermarkProfile
from loaded_dicewriter.core.stats import compute_detection, normal_sf, z_score
from loaded_dicewriter.inference.base import ModelInfo
from loaded_dicewriter.inference.model_registry import ModelSpec, get_model_spec
from loaded_dicewriter.settings import Settings
from loaded_dicewriter.watermark.kgw_inspectable import InspectableKGW

# Bias only the highest-logit candidates (covers virtually all sampling mass at
# typical temperatures). Full-vocab HMAC green masks are O(V) and dominate runtime;
# detection still uses exact per-token is_green on emitted tokens.
# Top-k logits that receive green-list bias. At T≈0.5–0.8 nearly all sampling mass
# sits well inside a few hundred candidates; 512 is a generous exact-enough band.
_BIAS_CANDIDATE_K = 512


class TransformersConfigError(RuntimeError):
    """Raised when transformers mode is selected without a usable local model."""


def select_device() -> str:
    """Pick MPS / CUDA / CPU without importing torch at module load in fake mode."""
    try:
        import torch  # type: ignore[import-not-found]
    except ImportError:
        return "cpu"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


@dataclass
class _BranchRuntime:
    label: str
    apply_watermark: bool
    token_ids: list[int]
    pieces: list[str]
    scored: int = 0
    green: int = 0
    excl_prefix: int = 0
    excl_repeated: int = 0
    seen_units: set[tuple[tuple[int, ...], int]] | None = None
    past_key_values: Any = None
    finished: bool = False

    def __post_init__(self) -> None:
        if self.seen_units is None:
            self.seen_units = set()

    @property
    def text(self) -> str:
        return "".join(self.pieces)


def flip_stats(control_ids: Sequence[int], loaded_ids: Sequence[int]) -> dict[str, float | int]:
    """Position-aligned flip metrics for coupled clean/loaded token sequences."""
    n = min(len(control_ids), len(loaded_ids))
    if n == 0:
        return {
            "aligned_tokens": 0,
            "flipped_tokens": 0,
            "flip_rate": 0.0,
            "match_prefix": 0,
        }
    flips = sum(1 for i in range(n) if int(control_ids[i]) != int(loaded_ids[i]))
    prefix = 0
    for i in range(n):
        if int(control_ids[i]) != int(loaded_ids[i]):
            break
        prefix += 1
    return {
        "aligned_tokens": n,
        "flipped_tokens": flips,
        "flip_rate": flips / n,
        "match_prefix": prefix,
    }


def _clone_past_key_values(past: Any) -> Any:
    """Deep-clone a transformers past_key_values tree so branches can diverge safely."""
    if past is None:
        return None

    def _clone_node(node: Any) -> Any:
        if node is None:
            return None
        if hasattr(node, "clone") and callable(node.clone):
            return node.clone()
        if isinstance(node, (list, tuple)):
            seq = [_clone_node(x) for x in node]
            return type(node)(seq)
        return node

    return _clone_node(past)


class TransformersBackend:
    """Explicit autoregressive loop with inspectable KGW bias on real logits."""

    def __init__(
        self,
        *,
        model_path: str | Path,
        spec: ModelSpec | None = None,
        device: str | None = None,
    ) -> None:
        self.model_path = Path(model_path)
        self.spec = spec or get_model_spec()
        self.device_name = device or select_device()
        self._model: Any = None
        self._tokenizer: Any = None
        self._loaded = False
        self.model_info = ModelInfo(
            id=self.spec.id,
            backend="transformers",
            revision=self.spec.revision,
            device=self.device_name,
        )

    @classmethod
    def from_settings(cls, settings: Settings) -> TransformersBackend:
        if settings.model.mode != "transformers":
            raise TransformersConfigError("model.mode is not 'transformers'")
        path = settings.model.model_path
        if not path:
            raise TransformersConfigError(
                "model.model_path is required when mode=transformers "
                "(no network download at runtime in v1)"
            )
        p = Path(path)
        if not p.exists():
            raise TransformersConfigError(
                f"local model path does not exist: {path} "
                "(place weights on disk; the app will not download them)"
            )
        return cls(model_path=p)

    async def load(self) -> None:
        if self._loaded:
            return
        await asyncio.to_thread(self._load_sync)

    def _load_sync(self) -> None:
        try:
            import torch
            from transformers import (  # type: ignore[import-not-found]
                AutoModelForCausalLM,
                AutoTokenizer,
            )
        except ImportError as exc:
            raise TransformersConfigError(
                "transformers and torch are required for model.mode=transformers"
            ) from exc

        tok = AutoTokenizer.from_pretrained(
            str(self.model_path),
            local_files_only=True,
            trust_remote_code=False,
            revision=self.spec.revision,
        )
        if tok.pad_token is None and tok.eos_token is not None:
            tok.pad_token = tok.eos_token

        dtype = torch.float32
        model = AutoModelForCausalLM.from_pretrained(
            str(self.model_path),
            local_files_only=True,
            trust_remote_code=False,
            revision=self.spec.revision,
            torch_dtype=dtype,
        )
        model.eval()
        model.to(self.device_name)
        # No gradients for inference.
        for p in model.parameters():
            p.requires_grad_(False)

        self._tokenizer = tok
        self._model = model
        self._loaded = True
        self.model_info = ModelInfo(
            id=self.spec.id,
            backend="transformers",
            revision=self.spec.revision,
            device=self.device_name,
            vocab_size=int(getattr(model.config, "vocab_size", 0)) or None,
        )

    async def unload(self) -> None:
        self._model = None
        self._tokenizer = None
        self._loaded = False

    async def generate_pair_events(
        self,
        *,
        prompt: str,
        seed: int,
        max_new_tokens: int,
        temperature: float,
        key: bytes,
        profile: WatermarkProfile,
        should_stop: Callable[[], bool],
    ) -> AsyncIterator[dict[str, Any]]:
        """Path-coupled clean/loaded sampling via common random numbers (CRN).

        At each step the model is forwarded **once** on the shared watermarked
        prefix. Clean samples from the base distribution with uniform ``u``;
        loaded applies KGW green-list logit bias to that **same** distribution
        and samples with the **same** ``u``. The loaded token is appended to the
        prefix (true watermarked trajectory). Clean is the CRN counterfactual
        twin — identical except where the bias flips the sample. Detector scores
        are measured on each branch's emitted token string.
        """
        if not self._loaded:
            await self.load()
        assert self._model is not None and self._tokenizer is not None

        import torch

        yield {"type": "branch_started", "branch": "control"}
        yield {"type": "branch_started", "branch": "loaded"}

        tokenizer = self._tokenizer
        model = self._model
        device = self.device_name
        shared_rng = random.Random(int(seed) & 0x7FFF_FFFF_FFFF_FFFF)

        control = _BranchRuntime(
            label="control", apply_watermark=False, token_ids=[], pieces=[]
        )
        loaded = _BranchRuntime(
            label="loaded", apply_watermark=True, token_ids=[], pieces=[]
        )

        encoded = tokenizer(prompt, return_tensors="pt")
        next_input = encoded["input_ids"].to(device)
        past_key_values: Any = None
        eos_id = tokenizer.eos_token_id

        with torch.inference_mode():
            for _step in range(max_new_tokens):
                if should_stop():
                    break

                # One forward on the shared watermarked prefix.
                outputs = model(
                    input_ids=next_input,
                    past_key_values=past_key_values,
                    use_cache=True,
                )
                past_key_values = outputs.past_key_values
                logits_t = outputs.logits[0, -1, :].detach().float().cpu()
                del outputs

                u = shared_rng.random()
                # Generation green-list context = last h tokens of the loaded path
                # (must match portable detection's context window).
                h = profile.context_width
                full_loaded = list(loaded.token_ids)
                gen_context = full_loaded[-h:] if h > 0 else []

                control_ev = self._sample_branch_event(
                    runtime=control,
                    logits_t=logits_t,
                    u=u,
                    temperature=temperature,
                    profile=profile,
                    key=key,
                    tokenizer=tokenizer,
                    gen_context_ids=gen_context,
                    apply_bias=False,
                )
                loaded_ev = self._sample_branch_event(
                    runtime=loaded,
                    logits_t=logits_t,
                    u=u,
                    temperature=temperature,
                    profile=profile,
                    key=key,
                    tokenizer=tokenizer,
                    gen_context_ids=gen_context,
                    apply_bias=True,
                )

                yield control_ev
                yield loaded_ev

                # Advance along the watermarked path (true KGW generation).
                loaded_id = int(loaded_ev["token_id"])
                next_input = torch.tensor([[loaded_id]], device=device)
                await asyncio.sleep(0)

                if eos_id is not None and loaded_id == eos_id:
                    break

        yield {"type": "branch_finished", "branch": "control"}
        yield {"type": "branch_finished", "branch": "loaded"}

    def _sample_branch_event(
        self,
        *,
        runtime: _BranchRuntime,
        logits_t: Any,
        u: float,
        temperature: float,
        profile: WatermarkProfile,
        key: bytes,
        tokenizer: Any,
        gen_context_ids: list[int],
        apply_bias: bool,
    ) -> dict[str, Any]:
        """Sample one branch from shared base logits with a fixed uniform ``u``."""
        import torch

        t = temperature if temperature > 0.0 else 1.0
        vocab_size = int(logits_t.numel())
        base_probs_t = torch.softmax(logits_t / t, dim=-1)

        if apply_bias:
            k = min(_BIAS_CANDIDATE_K, vocab_size)
            top_idx = torch.topk(logits_t, k=k).indices.tolist()
            green = green_ids_for_candidates(
                top_idx,
                context_ids=gen_context_ids,
                key=key,
                gamma=profile.gamma,
            )
            sample_logits = logits_t.clone()
            if green:
                g_idx = torch.tensor(sorted(green), dtype=torch.long)
                sample_logits[g_idx] = sample_logits[g_idx] + float(profile.delta)
            sample_probs_t = torch.softmax(sample_logits / t, dim=-1)
        else:
            sample_logits = logits_t
            sample_probs_t = base_probs_t

        u_clamped = 0.0 if u < 0.0 else (0.999999999999 if u >= 1.0 else float(u))
        cdf = torch.cumsum(sample_probs_t, dim=0)
        token_id = int(torch.searchsorted(cdf, torch.tensor(u_clamped)).item())
        if token_id >= vocab_size:
            token_id = vocab_size - 1

        piece = tokenizer.decode([token_id], skip_special_tokens=False)
        base_prob = float(base_probs_t[token_id].item())
        sample_prob = float(sample_probs_t[token_id].item())
        base_logit = float(logits_t[token_id].item())
        biased_logit = float(sample_logits[token_id].item()) if apply_bias else None

        # Portable detection bookkeeping uses this branch's own prior tokens.
        h = profile.context_width
        pos = len(runtime.token_ids)
        branch_context = list(runtime.token_ids)
        eligible = pos >= h
        exclusion_reason = None
        favored = False
        if not eligible:
            exclusion_reason = "missing_context"
            runtime.excl_prefix += 1
            favored = is_green(
                token_id, context_ids=gen_context_ids, key=key, gamma=profile.gamma
            )
        else:
            ctx = branch_context[-h:] if h else []
            unit = (tuple(ctx), token_id)
            assert runtime.seen_units is not None
            if profile.ignore_repeated_ngrams and unit in runtime.seen_units:
                eligible = False
                exclusion_reason = "repeated_ngram"
                runtime.excl_repeated += 1
                favored = is_green(
                    token_id, context_ids=ctx, key=key, gamma=profile.gamma
                )
            else:
                runtime.seen_units.add(unit)
                favored = is_green(
                    token_id, context_ids=ctx, key=key, gamma=profile.gamma
                )
                runtime.scored += 1
                if favored:
                    runtime.green += 1

        z_after = z_score(
            green_count=runtime.green,
            scored_count=runtime.scored,
            gamma=profile.gamma,
        )
        p_after = normal_sf(z_after) if runtime.scored else 1.0
        detection = compute_detection(
            num_tokens_total=pos + 1,
            num_tokens_scored=runtime.scored,
            num_green=runtime.green,
            gamma=profile.gamma,
            threshold=profile.z_threshold,
            min_scored_tokens=profile.min_scored_tokens,
            excluded_prefix_count=runtime.excl_prefix,
            excluded_repeated_count=runtime.excl_repeated,
        ).as_dict()

        top_k = 6
        order = torch.topk(base_probs_t, k=min(top_k, vocab_size)).indices.tolist()
        if token_id not in order:
            order = [token_id, *order][:top_k]
        cand_green = green_ids_for_candidates(
            order, context_ids=gen_context_ids, key=key, gamma=profile.gamma
        )
        top_before = [
            {
                "token_id": i,
                "text": tokenizer.decode([i], skip_special_tokens=False),
                "probability": float(base_probs_t[i].item()),
                "favored": i in cand_green,
            }
            for i in order
        ]
        order_a = torch.topk(sample_probs_t, k=min(top_k, vocab_size)).indices.tolist()
        if token_id not in order_a:
            order_a = [token_id, *order_a][:top_k]
        cand_green_a = green_ids_for_candidates(
            order_a, context_ids=gen_context_ids, key=key, gamma=profile.gamma
        )
        top_after = [
            {
                "token_id": i,
                "text": tokenizer.decode([i], skip_special_tokens=False),
                "probability": float(sample_probs_t[i].item()),
                "favored": i in cand_green_a,
            }
            for i in order_a
        ]

        bp = base_probs_t.clamp_min(1e-12)
        entropy = float((-(bp * bp.log2()).sum()).item())

        runtime.token_ids.append(token_id)
        runtime.pieces.append(piece)

        return {
            "type": "token",
            "branch": runtime.label,
            "position": pos,
            "token_id": token_id,
            "text": piece,
            "favored": bool(favored),
            "eligible": eligible,
            "exclusion_reason": exclusion_reason,
            "z_score": z_after,
            "p_value": p_after,
            "green_count": runtime.green,
            "scored_count": runtime.scored,
            "base_probability": base_prob,
            "biased_probability": sample_prob if apply_bias else None,
            "final_sampling_probability": sample_prob,
            "base_logit": base_logit,
            "biased_logit": biased_logit,
            "entropy": entropy,
            "context_ids": gen_context_ids[-h:] if h else [],
            "top_candidates_before": top_before,
            "top_candidates_after": top_after,
            "text_so_far": runtime.text,
            "detection": detection,
        }


def bias_logits_python(
    logits: Sequence[float],
    favored_mask: Sequence[bool],
    delta: float,
) -> list[float]:
    """Pure-Python bias helper used by unit tests without torch."""
    return [lg + (delta if fav else 0.0) for lg, fav in zip(logits, favored_mask, strict=True)]


def apply_kgw_to_logits(
    *,
    logits: Sequence[float],
    context_ids: Sequence[int],
    key: bytes,
    profile: WatermarkProfile,
) -> tuple[list[float], list[bool]]:
    """Inspectable KGW path on a plain logit vector (no model required)."""
    wm = InspectableKGW(key=key, profile=profile)
    mask = wm.favored_mask(context_ids=context_ids, vocab_size=len(logits))
    return bias_logits_python(logits, mask, profile.delta), mask
