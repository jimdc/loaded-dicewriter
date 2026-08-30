#!/usr/bin/env python3
"""Offline one-shot: freeze a gallery of real-model clean/loaded pairs.

Uses **coupled sampling** (common random numbers): at each step the clean and
loaded branches share one uniform draw. Clean samples from the base
distribution; loaded applies KGW green-list bias to the same step and samples
with that same draw. While histories match they stay word-for-word identical
except where the watermark flips the winner — the intuition pump for a nearly
invisible per-token bias that is still statistically detectable.

Runtime never imports this. Requires local torch + transformers + a small English
LM on disk (default: Qwen2.5-0.5B at MODEL_PATH). Does not change the app's default
weightless built-in engine.

Produces web/src/data/demo-gallery.json — browsable precomputed pairs with measured
flip-rates and z-scores. All text and scores are genuine model + KGW + detector.

Usage (from repo root):

    taskpolicy -b .venv/bin/python scripts/generate_demo_example.py

Environment:
    LDW_DEMO_MODEL_PATH  local model dir (default /tmp/ldw-models/Qwen2.5-0.5B)
    LDW_DEMO_MODEL_ID    short model id stamped into JSON (default Qwen2.5-0.5B)
    LDW_DEMO_HF_ID       HF id for ModelSpec (default Qwen/Qwen2.5-0.5B)
    LDW_DEMO_ONLY_ID     if set, regenerate only this gallery slot id
    LDW_DEMO_DEVICE      cpu|mps|cuda (default: mps if available else cpu)
    LDW_DEMO_TEMPERATURE sampling temperature (default 0.45)
    LDW_DEMO_MAX_NEW     max new tokens (default 48)
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
from dataclasses import asdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "server"))

from loaded_dicewriter.core.keys import TEACHING_KEY, key_fingerprint  # noqa: E402
from loaded_dicewriter.core.profiles import WatermarkProfile  # noqa: E402
from loaded_dicewriter.inference.model_registry import ModelSpec  # noqa: E402
from loaded_dicewriter.inference.transformers_backend import (  # noqa: E402
    TransformersBackend,
    flip_stats,
)

MODEL_PATH = os.environ.get("LDW_DEMO_MODEL_PATH", "/tmp/ldw-models/Qwen2.5-0.5B")
MODEL_ID = os.environ.get("LDW_DEMO_MODEL_ID", "Qwen2.5-0.5B")
HF_ID = os.environ.get("LDW_DEMO_HF_ID", "Qwen/Qwen2.5-0.5B")
OUT = REPO / "web" / "src" / "data" / "demo-gallery.json"
# Keep single-example alias for older import paths during transition.
OUT_LEGACY = REPO / "web" / "src" / "data" / "demo-example.json"
# Low temperature keeps mass on top tokens so CRN draws rarely flip under mild δ —
# both branches stay near-identical readable English. Qwen2.5-0.5B via HF transformers
# (logit access for KGW); Ollama APIs cannot do per-step logit biasing.
TEMPERATURE = float(os.environ.get("LDW_DEMO_TEMPERATURE", "0.45"))
MAX_NEW = int(os.environ.get("LDW_DEMO_MAX_NEW", "48"))

# Strength variants — offline fixtures only; runtime still uses teaching-kgw default.
# Lead examples use light δ so CRN pairs stay near-identical (low flip-rate) while
# loaded z stays clearly above clean. One stronger slot remains for contrast.
PROFILE_SUBTLE = WatermarkProfile(
    id="kgw-subtle",
    name="Subtle bias",
    gamma=0.25,
    delta=0.8,
    context_width=1,
    ignore_repeated_ngrams=True,
    z_threshold=4.0,
    min_scored_tokens=20,
)
PROFILE_LIGHT = WatermarkProfile(
    id="kgw-light",
    name="Light bias",
    gamma=0.5,
    delta=0.9,
    context_width=1,
    ignore_repeated_ngrams=True,
    z_threshold=4.0,
    min_scored_tokens=20,
)
PROFILE_DEFAULT = WatermarkProfile(
    id="teaching-kgw",
    name="Teaching KGW",
    gamma=0.25,
    delta=1.5,
    context_width=1,
    ignore_repeated_ngrams=True,
    z_threshold=4.0,
    min_scored_tokens=20,
)
PROFILE_STRONG = WatermarkProfile(
    id="kgw-strong",
    name="Strong bias",
    gamma=0.25,
    delta=2.0,
    context_width=1,
    ignore_repeated_ngrams=True,
    z_threshold=4.0,
    min_scored_tokens=20,
)

# Gallery slots: LEAD with subtle pairs, one strong for contrast.
# target_flip_max: prefer pairs below this flip-rate when possible.
GALLERY_SLOTS: list[dict] = [
    {
        "id": "neighborhood-subtle",
        "label": "Neighborhood stores",
        "strength_label": "subtle",
        "prompt": "Cities develop many small neighborhood stores because",
        "profile": PROFILE_SUBTLE,
        "target_flip_max": 0.16,
        "seeds": list(range(1, 180))
        + [101, 202, 303, 404, 512, 777, 999, 1234, 2024, 3141, 4242, 5555, 7777, 8888, 9001],
    },
    {
        "id": "library-subtle",
        "label": "Quiet library",
        "strength_label": "subtle",
        "prompt": "A quiet library on a rainy afternoon is a place where",
        "profile": PROFILE_SUBTLE,
        "target_flip_max": 0.16,
        "seeds": list(range(1, 180))
        + [101, 202, 303, 512, 777, 999, 1234, 2024, 3141, 4242, 5555, 8888],
    },
    {
        "id": "harbor-light",
        "label": "Morning harbor",
        "strength_label": "light",
        "prompt": "In the early morning, the harbor was calm and",
        "profile": PROFILE_LIGHT,
        "target_flip_max": 0.20,
        "seeds": list(range(1, 160)) + [101, 202, 303, 777, 2024, 4242, 5555, 8888],
    },
    {
        "id": "opensource-default",
        "label": "Open-source software",
        "strength_label": "default",
        "prompt": "Open-source software thrives when communities",
        "profile": PROFILE_DEFAULT,
        "target_flip_max": 0.24,
        "seeds": list(range(1, 160))
        + [101, 202, 303, 404, 512, 777, 999, 1234, 2024, 3141, 8888, 9001],
    },
    {
        "id": "baking-default",
        "label": "Baking bread",
        "strength_label": "default",
        "prompt": "The science of baking bread begins with understanding that",
        "profile": PROFILE_DEFAULT,
        "target_flip_max": 0.24,
        "seeds": list(range(1, 160)) + [101, 202, 404, 777, 3141, 5555, 8888],
    },
    {
        "id": "skills-strong",
        "label": "Learning a skill",
        "strength_label": "strong",
        "prompt": "The best way to learn a new skill is to practice carefully so that",
        "profile": PROFILE_STRONG,
        # Strong is for contrast — allow higher flip-rate, still prefer readable English.
        "target_flip_max": 0.40,
        "seeds": list(range(1, 120)) + [101, 404, 777, 999, 3141, 8888],
    },
]


_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff\u0400-\u04ff\u0600-\u06ff]")
_SPECIAL_RE = re.compile(r"<\|[^|>]+?\|>")
_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def clean_model_text(text: str) -> str:
    t = _SPECIAL_RE.sub("", text)
    t = _CTRL_RE.sub("", t)
    return t.strip()


def first_paragraph(text: str) -> str:
    t = clean_model_text(text)
    # Prefer first prose block before blank lines or markdown-ish list dumps.
    return re.split(r"\n\s*\n", t, maxsplit=1)[0].strip()


def prose_quality(text: str) -> float:
    """Heuristic: longer grammatical-looking English first paragraph scores higher."""
    first = first_paragraph(text)
    if len(first) < 40:
        return -100.0
    if _CJK_RE.search(first):
        return -100.0
    if re.search(r"\b[A-D]\.\s", first) or "____" in first:
        return -100.0
    words = re.findall(r"[A-Za-z']+", first)
    if len(words) < 14:
        return -100.0
    newlines = first.count("\n")
    alpha = sum(c.isalpha() or c in " .,;:'\"-!?" for c in first) / max(len(first), 1)
    score = len(words) * 1.5 - newlines * 3 + 35 * alpha
    if first.count("  ") > 3:
        score -= 5
    # Bigram diversity — word salad repeats or stutters.
    if len(words) >= 6:
        bigrams = list(zip(words, words[1:], strict=False))
        uniq = len(set(bigrams)) / max(len(bigrams), 1)
        score += 25.0 * uniq
    # Average word length in a readable band.
    avg_len = sum(len(w) for w in words) / len(words)
    if 3.2 <= avg_len <= 7.5:
        score += 8.0
    else:
        score -= 6.0
    # Reject triple word stutters.
    if re.search(r"\b(\w+)(?:[,\s]+\1){2,}\b", first, flags=re.I):
        score -= 40.0
    # Penalize heavy digit / code-ish dumps.
    digits = sum(c.isdigit() for c in first)
    if digits > 12:
        score -= 15.0
    # Prefer continuous prose (fewer hard line breaks mid-paragraph).
    if newlines == 0:
        score += 6.0
    return score


def looks_like_english(text: str) -> bool:
    """Reject non-Latin, exam dumps, EOS junk, and near-empty first paragraphs."""
    first = first_paragraph(text)
    if _CJK_RE.search(first):
        return False
    # Qwen base often switches into multiple-choice exam scaffolding — reject.
    if re.search(r"\b[A-D]\.\s", first):
        return False
    if "____" in first or "答案" in first or "正确" in first or "错误" in first:
        return False
    if re.search(r"\b(True|False)\s*/\s*(True|False)\b", first, flags=re.I):
        return False
    words = re.findall(r"[A-Za-z']+", first)
    if len(words) < 16:
        return False
    if first.count("\n") > 3:
        return False
    if re.search(r"\b(\w+)(?:[,\s]+\1){2,}\b", first, flags=re.I):
        return False
    # Require mostly Latin letters among non-space chars.
    non_space = [c for c in first if not c.isspace()]
    if not non_space:
        return False
    latin = sum(c.isascii() and (c.isalpha() or c in ".,;:'\"-!?()") for c in non_space)
    if latin / len(non_space) < 0.88:
        return False
    return True


def token_event_to_fixture(ev: dict) -> dict:
    return {
        "position": ev["position"],
        "token_id": ev["token_id"],
        "text": ev["text"],
        "favored": ev["favored"],
        "eligible": ev["eligible"],
        "exclusion_reason": ev["exclusion_reason"],
        "z_score": ev["z_score"],
        "p_value": ev["p_value"],
        "green_count": ev["green_count"],
        "scored_count": ev["scored_count"],
        "base_probability": ev["base_probability"],
        "biased_probability": ev["biased_probability"],
        "final_sampling_probability": ev["final_sampling_probability"],
        "base_logit": ev["base_logit"],
        "biased_logit": ev["biased_logit"],
        "entropy": ev["entropy"],
        "context_ids": ev["context_ids"],
        "top_candidates_before": ev["top_candidates_before"],
        "top_candidates_after": ev["top_candidates_after"],
    }


async def generate_pair(
    backend: TransformersBackend,
    *,
    prompt: str,
    seed: int,
    profile: WatermarkProfile,
):
    tokens: dict[str, list] = {"control": [], "loaded": []}
    texts = {"control": "", "loaded": ""}
    detections: dict = {}
    async for ev in backend.generate_pair_events(
        prompt=prompt,
        seed=seed,
        max_new_tokens=MAX_NEW,
        temperature=TEMPERATURE,
        key=TEACHING_KEY,
        profile=profile,
        should_stop=lambda: False,
    ):
        if ev["type"] != "token":
            continue
        b = ev["branch"]
        tokens[b].append(token_event_to_fixture(ev))
        texts[b] = ev["text_so_far"]
        detections[b] = ev["detection"]
    # Prefer first-paragraph display text so UI passages stay readable when the
    # model later digresses; token arrays (and z-scores) stay full-length measured.
    return texts, tokens, detections


def pair_flip_stats(tokens: dict) -> dict[str, float | int]:
    c_ids = [t["token_id"] for t in tokens["control"]]
    l_ids = [t["token_id"] for t in tokens["loaded"]]
    return flip_stats(c_ids, l_ids)


def qualifies(
    texts: dict,
    detections: dict,
    tokens: dict,
    profile: WatermarkProfile,
    *,
    target_flip_max: float,
) -> bool:
    """Acceptable gallery pair: readable English, CRN subtlety, clear z contrast."""
    cz = detections["control"]["z_score"]
    lz = detections["loaded"]["z_score"]
    stats = pair_flip_stats(tokens)
    flip_rate = float(stats["flip_rate"])
    flipped = int(stats["flipped_tokens"])

    # Path-coupled: loaded is free watermarked English; clean is the CRN twin
    # (nearly identical when flip-rate is low). Require loaded quality first.
    lq = prose_quality(texts["loaded"])
    cq = prose_quality(texts["control"])
    if lq < 60:
        return False
    if not looks_like_english(texts["loaded"]):
        return False
    # Clean must also read as English — path-coupled CRN only keeps both coherent
    # when flip-rate stays modest.
    if not looks_like_english(texts["control"]):
        return False
    if cq < 50:
        return False
    if detections["control"]["detected"]:
        return False
    if flipped < 1:
        return False
    # Prefer enough scored tokens for a meaningful z (formal threshold uses ≥20).
    scored = int(detections["loaded"].get("num_tokens_scored") or 0)
    if scored < 18:
        return False
    # Subtlety: reject near-total rewrites for non-strong slots.
    if profile.delta < 2.2 and flip_rate > min(0.35, target_flip_max + 0.14):
        return False
    if profile.delta >= 2.2 and flip_rate > 0.60:
        return False

    # Detection contrast: loaded clearly above clean. Mild δ can still lift z.
    if profile.delta <= 1.0:
        return lz >= 1.8 and lz > cz + 0.7 and cz < 3.0
    if profile.delta <= 1.5:
        return lz >= 2.0 and lz > cz + 0.9 and cz < 3.0
    if profile.delta <= 2.2:
        if detections["loaded"]["detected"]:
            return cz < 3.0 and lz >= profile.z_threshold
        return lz >= 2.5 and lz > cz + 1.2 and cz < 3.0
    # Strong
    if detections["loaded"]["detected"]:
        return cz < 3.0 and lz >= profile.z_threshold
    return lz >= 3.0 and lz > cz + 1.5 and cz < 3.0


def rank(
    texts: dict,
    detections: dict,
    tokens: dict,
    *,
    target_flip_max: float,
) -> float:
    """Higher is better: long match prefix, low flip-rate, z contrast, prose."""
    cz = detections["control"]["z_score"]
    lz = detections["loaded"]["z_score"]
    stats = pair_flip_stats(tokens)
    flip_rate = float(stats["flip_rate"])
    prefix = int(stats["match_prefix"])
    aligned = max(int(stats["aligned_tokens"]), 1)
    cq = prose_quality(texts["control"])
    lq = prose_quality(texts["loaded"])

    z_gap = lz - max(cz, 0.0)
    # Match prefix is the main subtlety signal under free-running CRN (after the
    # first flip, histories diverge). Reward long shared heads heavily.
    prefix_score = 22.0 * (prefix / aligned)
    if prefix >= 12:
        prefix_score += 5.0
    if prefix >= 20:
        prefix_score += 8.0

    if flip_rate <= target_flip_max:
        flip_score = 14.0 * (1.0 - flip_rate / max(target_flip_max, 0.05))
    else:
        flip_score = -18.0 * (flip_rate - target_flip_max)

    prose = 0.08 * (cq + lq)
    # Both sides readable is the product requirement.
    if cq >= 50 and lq >= 50:
        prose += 10.0
    detect_bonus = 3.0 if detections["loaded"].get("detected") else (1.0 if lz >= 2.5 else 0.0)
    if z_gap < 1.0:
        z_gap -= 6.0
    # Prefer a few real flips (not zero, not a total rewrite).
    flipped = int(stats["flipped_tokens"])
    if 1 <= flipped <= max(4, aligned // 4):
        flip_score += 6.0
    return z_gap + flip_score + prefix_score + prose + detect_bonus


def profile_meta(p: WatermarkProfile) -> dict:
    return asdict(p)


def build_example(
    *,
    slot: dict,
    seed: int,
    texts: dict,
    tokens: dict,
    dets: dict,
) -> dict:
    profile: WatermarkProfile = slot["profile"]
    stats = pair_flip_stats(tokens)
    return {
        "id": slot["id"],
        "label": slot["label"],
        "strength_label": slot["strength_label"],
        "prompt": slot["prompt"],
        "seed": seed,
        "max_new_tokens": MAX_NEW,
        "temperature": TEMPERATURE,
        "sampling": "coupled_crn_path",
        "profile_id": profile.id,
        "profile": profile_meta(profile),
        "key_fingerprint": key_fingerprint(TEACHING_KEY),
        "engine": MODEL_ID,
        "model": MODEL_ID,
        "flip_rate": stats["flip_rate"],
        "flipped_tokens": stats["flipped_tokens"],
        "aligned_tokens": stats["aligned_tokens"],
        "match_prefix": stats["match_prefix"],
        "note": (
            f"Frozen offline TransformersBackend ({MODEL_ID}) + {profile.name} "
            f"(γ={profile.gamma:g}, δ={profile.delta:g}, h={profile.context_width}, "
            f"seed={seed}, max_new_tokens={MAX_NEW}, sampling=coupled_crn_path). "
            f"Measured flip-rate={float(stats['flip_rate']) * 100:.1f}% "
            f"({stats['flipped_tokens']}/{stats['aligned_tokens']} tokens), "
            f"match_prefix={stats['match_prefix']}. "
            "Real sampling + KGW + detector — not hand-faked. "
            "Runtime default remains the weightless built-in engine."
        ),
        "control": {
            "text": texts["control"],
            "tokens": tokens["control"],
            "detection": dets["control"],
        },
        "loaded": {
            "text": texts["loaded"],
            "tokens": tokens["loaded"],
            "detection": dets["loaded"],
        },
    }


async def fill_slot(backend: TransformersBackend, slot: dict) -> dict:
    profile: WatermarkProfile = slot["profile"]
    target_flip_max = float(slot.get("target_flip_max", 0.4))
    best_q: dict | None = None
    best_rank = -1e9
    best_any: dict | None = None
    best_any_rank = -1e9

    for seed in slot["seeds"]:
        t0 = time.time()
        texts, tokens, dets = await generate_pair(
            backend, prompt=slot["prompt"], seed=seed, profile=profile
        )
        dt = time.time() - t0
        stats = pair_flip_stats(tokens)
        r = rank(texts, dets, tokens, target_flip_max=target_flip_max)
        ok = qualifies(texts, dets, tokens, profile, target_flip_max=target_flip_max)
        print(
            f"  [{slot['id']}] seed={seed} ok={ok} "
            f"cz={dets['control']['z_score']:.2f} lz={dets['loaded']['z_score']:.2f} "
            f"flip={float(stats['flip_rate']) * 100:.0f}% "
            f"({stats['flipped_tokens']}/{stats['aligned_tokens']}) "
            f"prefix={stats['match_prefix']} "
            f"cq={prose_quality(texts['control']):.0f} lq={prose_quality(texts['loaded']):.0f} "
            f"rank={r:.1f} t={dt:.1f}s",
            flush=True,
        )
        print("    C:", first_paragraph(texts["control"])[:140].replace("\n", "\\n"), flush=True)
        print("    L:", first_paragraph(texts["loaded"])[:140].replace("\n", "\\n"), flush=True)
        example = build_example(
            slot=slot, seed=seed, texts=texts, tokens=tokens, dets=dets
        )
        if r > best_any_rank:
            best_any_rank = r
            best_any = example
        if ok and r > best_rank:
            best_rank = r
            best_q = example
            # Early stop on a high-quality subtle pair (both sides readable English).
            flip_rate = float(stats["flip_rate"])
            lz = dets["loaded"]["z_score"]
            cz = dets["control"]["z_score"]
            if (
                flip_rate <= target_flip_max
                and lz >= 2.2
                and lz > cz + 0.8
                and prose_quality(texts["loaded"]) >= 70
                and prose_quality(texts["control"]) >= 55
                and int(stats["flipped_tokens"]) >= 1
            ):
                break

    if best_q is not None:
        return best_q
    if best_any is not None:
        stats = {
            "flip_rate": best_any["flip_rate"],
            "flipped_tokens": best_any["flipped_tokens"],
            "aligned_tokens": best_any["aligned_tokens"],
            "match_prefix": best_any["match_prefix"],
        }
        texts = {
            "control": best_any["control"]["text"],
            "loaded": best_any["loaded"]["text"],
        }
        dets = {
            "control": best_any["control"]["detection"],
            "loaded": best_any["loaded"]["detection"],
        }
        tokens = {
            "control": best_any["control"]["tokens"],
            "loaded": best_any["loaded"]["tokens"],
        }
        if qualifies(texts, dets, tokens, profile, target_flip_max=target_flip_max):
            return best_any
        cq = prose_quality(best_any["control"]["text"])
        lq = prose_quality(best_any["loaded"]["text"])
        lz = best_any["loaded"]["detection"]["z_score"]
        cz = best_any["control"]["detection"]["z_score"]
        # Relaxed accept still requires readable English on BOTH sides.
        if (
            cq >= 45
            and lq >= 55
            and looks_like_english(best_any["loaded"]["text"])
            and looks_like_english(best_any["control"]["text"])
            and lz > cz
            and int(stats["flipped_tokens"]) >= 1
        ):
            print(f"  [{slot['id']}] WARNING: relaxed accept (best available)", flush=True)
            return best_any
    raise RuntimeError(f"No acceptable pair for slot {slot['id']}")


def default_device() -> str:
    env = os.environ.get("LDW_DEMO_DEVICE")
    if env:
        return env
    try:
        import torch

        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
    except ImportError:
        pass
    return "cpu"


async def main() -> None:
    model_path = Path(MODEL_PATH)
    if not model_path.exists():
        raise SystemExit(
            f"Model path missing: {model_path}\n"
            "Download once, e.g. HF_HUB_DISABLE_XET=1 huggingface-cli download "
            f"{HF_ID} --local-dir {model_path}"
        )

    only_id = os.environ.get("LDW_DEMO_ONLY_ID")
    slots = [s for s in GALLERY_SLOTS if only_id is None or s["id"] == only_id]
    if not slots:
        raise SystemExit(f"Unknown LDW_DEMO_ONLY_ID={only_id!r}")

    existing: dict | None = None
    if OUT.exists() and only_id:
        existing = json.loads(OUT.read_text())

    spec = ModelSpec(
        id=MODEL_ID,
        hf_id=HF_ID,
        revision=None,
        backend="transformers",
        dtype="float32",
        chat_template=False,
        max_context_tokens=2048,
        recommended_max_new_tokens=80,
        local_path=str(model_path),
    )
    device = default_device()
    backend = TransformersBackend(model_path=model_path, spec=spec, device=device)
    await backend.load()
    print(f"model={MODEL_ID} path={model_path} device={device}", flush=True)
    print(
        f"sampling=coupled_crn_path temperature={TEMPERATURE} max_new={MAX_NEW}",
        flush=True,
    )

    examples: list[dict] = []
    if existing and only_id:
        examples = [e for e in existing.get("examples", []) if e.get("id") != only_id]

    for slot in slots:
        print(
            f"\n=== slot {slot['id']} ({slot['strength_label']}, "
            f"δ={slot['profile'].delta}) ===",
            flush=True,
        )
        example = await fill_slot(backend, slot)
        examples.append(example)
        order = {s["id"]: i for i, s in enumerate(GALLERY_SLOTS)}
        examples.sort(key=lambda e: order.get(e["id"], 999))

        gallery = {
            "version": 3,
            "model": MODEL_ID,
            "engine": MODEL_ID,
            "sampling": "coupled_crn_path",
            "key_fingerprint": key_fingerprint(TEACHING_KEY),
            "note": (
                f"Gallery of frozen offline TransformersBackend ({MODEL_ID}) pairs "
                "generated with path-coupled common-random-number sampling: one base "
                "distribution per step on the watermarked prefix; clean samples base, "
                "loaded samples green-list-biased, same uniform draw. Texts stay "
                "near-identical except where the bias flips a token. Flip-rates and "
                "z-scores are measured, not authored. Runtime default remains the "
                "weightless built-in engine; only this JSON ships."
            ),
            "examples": examples,
        }
        OUT.write_text(json.dumps(gallery, indent=2) + "\n")
        print(
            f"  checkpoint {OUT} ({len(examples)} examples) "
            f"flip={float(example['flip_rate']) * 100:.0f}% "
            f"cz={example['control']['detection']['z_score']:.2f} "
            f"lz={example['loaded']['detection']['z_score']:.2f}",
            flush=True,
        )

    if len(examples) < 4:
        raise SystemExit(f"Gallery too small: {len(examples)} examples (need ≥4)")

    first = examples[0]
    OUT_LEGACY.write_text(json.dumps(first, indent=2) + "\n")
    print(f"\nWROTE {OUT} ({len(examples)} examples)", flush=True)
    print(f"WROTE {OUT_LEGACY} (first example alias)", flush=True)
    print("\nPer-example report:", flush=True)
    for e in examples:
        print(
            f"  - {e['id']}: prompt={e['prompt'][:50]!r}… "
            f"flip={float(e['flip_rate']) * 100:.1f}% "
            f"({e['flipped_tokens']}/{e['aligned_tokens']}) "
            f"prefix={e['match_prefix']} "
            f"cz={e['control']['detection']['z_score']:.2f} "
            f"lz={e['loaded']['detection']['z_score']:.2f} "
            f"δ={e['profile']['delta']}",
            flush=True,
        )
        print(
            f"    L: {first_paragraph(e['loaded']['text'])[:160].replace(chr(10), ' ')}",
            flush=True,
        )
        print(
            f"    C: {first_paragraph(e['control']['text'])[:160].replace(chr(10), ' ')}",
            flush=True,
        )


if __name__ == "__main__":
    asyncio.run(main())
