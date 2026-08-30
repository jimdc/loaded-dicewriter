"""Unit tests for KGW green-list determinism, biasing, and sampling honesty."""

from __future__ import annotations

import math

from loaded_dicewriter.core.keys import TEACHING_KEY, key_fingerprint, parse_key_material
from loaded_dicewriter.core.prf import green_mask, green_token_ids, is_green
from loaded_dicewriter.core.profiles import TEACHING_KGW
from loaded_dicewriter.generation.fake_engine import TOY_VOCAB, FakeEngine
from loaded_dicewriter.generation.sampler import sample_categorical, softmax
from loaded_dicewriter.watermark.kgw_inspectable import InspectableKGW


def test_teaching_key_fingerprint_matches_ui() -> None:
    assert key_fingerprint(TEACHING_KEY) == "4ac2"


def test_same_key_and_context_same_green_list() -> None:
    ctx = [3, 7]
    a = green_mask(context_ids=ctx, vocab_size=40, key=TEACHING_KEY, gamma=0.25)
    b = green_mask(context_ids=ctx, vocab_size=40, key=TEACHING_KEY, gamma=0.25)
    assert a == b
    assert any(a)
    assert not all(a)


def test_different_key_changes_green_list() -> None:
    ctx = [1, 2, 3]
    key_a = TEACHING_KEY
    key_b = parse_key_material("another-secret-key")
    a = green_token_ids(context_ids=ctx, vocab_size=40, key=key_a, gamma=0.25)
    b = green_token_ids(context_ids=ctx, vocab_size=40, key=key_b, gamma=0.25)
    assert a != b


def test_green_fraction_approximates_gamma() -> None:
    """Over many contexts, membership rate ≈ γ."""
    gamma = 0.25
    vocab = 64
    hits = 0
    trials = 0
    for ctx0 in range(50):
        mask = green_mask(
            context_ids=[ctx0],
            vocab_size=vocab,
            key=TEACHING_KEY,
            gamma=gamma,
        )
        hits += sum(1 for m in mask if m)
        trials += vocab
    rate = hits / trials
    assert abs(rate - gamma) < 0.03


def test_only_favored_logits_receive_delta() -> None:
    wm = InspectableKGW(key=TEACHING_KEY, profile=TEACHING_KGW)
    logits = [0.0] * 20
    bias = wm.bias_logits(context_ids=[5], logits=logits)
    for i, (before, after, fav) in enumerate(
        zip(logits, bias.logits_after, bias.favored_mask, strict=True)
    ):
        if fav:
            assert after == before + TEACHING_KGW.delta
        else:
            assert after == before
        _ = i


def test_probabilities_normalize_after_bias() -> None:
    wm = InspectableKGW(key=TEACHING_KEY, profile=TEACHING_KGW)
    logits = [math.log(i + 1) for i in range(len(TOY_VOCAB))]
    bias = wm.bias_logits(context_ids=[2], logits=logits)
    probs = softmax(bias.logits_after)
    assert abs(sum(probs) - 1.0) < 1e-9
    assert all(p >= 0.0 for p in probs)


def test_selected_token_traceable_to_sampling_distribution() -> None:
    engine = FakeEngine(default_length=16)
    result = engine.generate_pair_traced("bodegas and shops", seed=42, length=16)
    loaded = result["loaded"]
    assert len(loaded.tokens) == 16
    for tok in loaded.tokens:
        assert 0 <= tok.token_id < len(TOY_VOCAB)
        assert tok.text == TOY_VOCAB[tok.token_id]
        assert 0.0 <= tok.final_sampling_probability <= 1.0
        # Final prob must match a candidate row when present.
        after_ids = {c.token_id for c in tok.top_candidates_after}
        assert tok.token_id in after_ids


def test_loaded_branch_elevates_green_rate_vs_control() -> None:
    engine = FakeEngine(default_length=80)
    total_green_loaded = 0
    total_scored_loaded = 0
    total_green_control = 0
    total_scored_control = 0
    for seed in range(8):
        pair = engine.generate_pair_traced("why cities grow shops", seed=seed, length=80)
        total_green_loaded += int(pair["loaded"].detection["num_green"])
        total_scored_loaded += int(pair["loaded"].detection["num_tokens_scored"])
        total_green_control += int(pair["control"].detection["num_green"])
        total_scored_control += int(pair["control"].detection["num_tokens_scored"])
    loaded_rate = total_green_loaded / max(1, total_scored_loaded)
    control_rate = total_green_control / max(1, total_scored_control)
    # Control near γ; loaded materially higher.
    assert control_rate < 0.40
    assert loaded_rate > control_rate + 0.05


def test_control_and_loaded_differ_and_are_deterministic() -> None:
    engine = FakeEngine()
    a = engine.generate_pair("why cities grow shops", seed=7, length=20)
    b = engine.generate_pair("why cities grow shops", seed=7, length=20)
    assert a.control.text == b.control.text
    assert a.loaded.text == b.loaded.text
    assert a.control.text != a.loaded.text
    assert a.control.text.endswith(".")


def test_sample_categorical_respects_degenerate_distribution() -> None:
    import random

    rng = random.Random(0)
    probs = [0.0, 0.0, 1.0, 0.0]
    for _ in range(20):
        assert sample_categorical(probs, rng) == 2


def test_is_green_matches_mask() -> None:
    ctx = [9]
    mask = green_mask(context_ids=ctx, vocab_size=30, key=TEACHING_KEY, gamma=0.25)
    for i, m in enumerate(mask):
        assert is_green(i, context_ids=ctx, key=TEACHING_KEY, gamma=0.25) is m
