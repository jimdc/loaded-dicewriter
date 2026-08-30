"""Common-random-number coupling: clean and loaded share each step's draw."""

from __future__ import annotations

from loaded_dicewriter.core.profiles import WatermarkProfile
from loaded_dicewriter.generation.fake_engine import FakeEngine
from loaded_dicewriter.generation.sampler import sample_categorical_u, softmax
from loaded_dicewriter.inference.transformers_backend import flip_stats


def test_sample_categorical_u_inverse_cdf() -> None:
    probs = [0.1, 0.2, 0.7]
    assert sample_categorical_u(probs, 0.0) == 0
    assert sample_categorical_u(probs, 0.05) == 0
    assert sample_categorical_u(probs, 0.15) == 1
    assert sample_categorical_u(probs, 0.99) == 2


def test_same_u_same_token_without_bias() -> None:
    logits = [0.0, 1.0, -0.5, 0.2]
    probs = softmax(logits, temperature=1.0)
    for u in (0.01, 0.2, 0.5, 0.8, 0.99):
        assert sample_categorical_u(probs, u) == sample_categorical_u(probs, u)


def test_flip_stats_prefix_and_rate() -> None:
    stats = flip_stats([1, 2, 3, 4], [1, 2, 9, 4])
    assert stats["aligned_tokens"] == 4
    assert stats["flipped_tokens"] == 1
    assert stats["match_prefix"] == 2
    assert abs(float(stats["flip_rate"]) - 0.25) < 1e-9


def test_fake_engine_crn_identical_when_delta_zero() -> None:
    """With δ=0 the biased dist equals the base dist → CRN keeps branches equal."""
    profile = WatermarkProfile(
        id="zero-delta",
        name="Zero",
        gamma=0.25,
        delta=0.0,
        context_width=1,
        ignore_repeated_ngrams=True,
        z_threshold=4.0,
        min_scored_tokens=20,
    )
    engine = FakeEngine(profile=profile, temperature=1.0)
    pair = engine.generate_pair_traced("bodegas and shops", seed=42, length=24)
    c_ids = pair["control"].token_ids
    l_ids = pair["loaded"].token_ids
    assert c_ids == l_ids
    assert pair["control"].text == pair["loaded"].text


def test_fake_engine_path_coupled_sparse_flips() -> None:
    """Path-coupled CRN: only watermark bias flips tokens; re-runs are deterministic."""
    engine = FakeEngine(temperature=1.0)
    pair = engine.generate_pair_traced("why cities grow shops", seed=7, length=32)
    c_ids = pair["control"].token_ids
    l_ids = pair["loaded"].token_ids
    stats = flip_stats(c_ids, l_ids)
    pair2 = engine.generate_pair_traced("why cities grow shops", seed=7, length=32)
    assert pair2["control"].token_ids == c_ids
    assert pair2["loaded"].token_ids == l_ids
    # Same length: path coupling advances one shared trajectory.
    assert len(c_ids) == len(l_ids)
    prefix = int(stats["match_prefix"])
    assert c_ids[:prefix] == l_ids[:prefix]
    if prefix < len(c_ids):
        assert c_ids[prefix] != l_ids[prefix]
    # Flips should be a fraction of tokens, not a full rewrite, for moderate δ.
    assert float(stats["flip_rate"]) < 0.85


def test_fake_engine_delta_zero_z_scores_match() -> None:
    profile = WatermarkProfile(
        id="zero-delta",
        name="Zero",
        gamma=0.25,
        delta=0.0,
        context_width=1,
        ignore_repeated_ngrams=True,
        z_threshold=4.0,
        min_scored_tokens=10,
    )
    engine = FakeEngine(profile=profile)
    pair = engine.generate_pair_traced("neighborhood stores", seed=3, length=20)
    assert pair["control"].detection["z_score"] == pair["loaded"].detection["z_score"]
