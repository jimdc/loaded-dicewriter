"""Deterministic toy engine tests."""

from __future__ import annotations

from loaded_dicewriter.generation.fake_engine import FakeEngine


def test_same_seed_same_output() -> None:
    engine = FakeEngine()
    a = engine.generate_pair("bodegas", seed=42, length=12)
    b = engine.generate_pair("bodegas", seed=42, length=12)
    assert a.control.text == b.control.text
    assert a.loaded.text == b.loaded.text
    assert [t.token_id for t in a.control.tokens] == [t.token_id for t in b.control.tokens]


def test_different_seed_changes_output() -> None:
    engine = FakeEngine()
    a = engine.generate_pair("bodegas", seed=1, length=16)
    b = engine.generate_pair("bodegas", seed=2, length=16)
    assert a.control.text != b.control.text or a.loaded.text != b.loaded.text


def test_control_and_loaded_differ() -> None:
    engine = FakeEngine()
    result = engine.generate_pair("why cities grow shops", seed=7, length=16)
    assert result.control.text != result.loaded.text
    assert len(result.control.tokens) == len(result.loaded.tokens)
    assert result.control.text.endswith(".")


def test_traced_pair_includes_before_after_candidates() -> None:
    engine = FakeEngine()
    pair = engine.generate_pair_traced("neighborhood stores", seed=3, length=10)
    loaded = pair["loaded"]
    assert loaded.tokens
    tok = loaded.tokens[-1]
    assert tok.top_candidates_before
    assert tok.top_candidates_after
    # Loaded applies bias: biased logit is base + δ when favored.
    favored = next(t for t in loaded.tokens if t.eligible and t.favored)
    assert favored.biased_logit is not None
    assert favored.biased_logit == favored.base_logit + engine.profile.delta
