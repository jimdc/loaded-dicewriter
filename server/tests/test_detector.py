"""Statistical detector: z-score, p-value, exclusions, wrong-key null behavior."""

from __future__ import annotations

import math

from loaded_dicewriter.core.keys import TEACHING_KEY, parse_key_material
from loaded_dicewriter.core.profiles import TEACHING_KGW
from loaded_dicewriter.core.stats import compute_detection, normal_sf, z_score
from loaded_dicewriter.generation.fake_engine import FakeEngine
from loaded_dicewriter.watermark.kgw_inspectable import InspectableKGW


def test_z_score_known_fixture() -> None:
    # T=100, γ=0.25 → expected 25; K=40
    # z = (40 - 25) / sqrt(100*0.25*0.75) = 15 / sqrt(18.75) ≈ 3.4641
    z = z_score(green_count=40, scored_count=100, gamma=0.25)
    assert abs(z - 15 / math.sqrt(18.75)) < 1e-9


def test_z_score_zero_scored_is_safe() -> None:
    assert z_score(green_count=0, scored_count=0, gamma=0.25) == 0.0
    result = compute_detection(
        num_tokens_total=0,
        num_tokens_scored=0,
        num_green=0,
        gamma=0.25,
        threshold=4.0,
        min_scored_tokens=20,
    )
    assert result.verdict == "insufficient_scored_tokens"
    assert result.p_value == 1.0
    assert not result.detected


def test_normal_sf_known_values() -> None:
    # Φ̄(0) = 0.5; Φ̄(1.96) ≈ 0.025; Φ̄(4) is tiny
    assert abs(normal_sf(0.0) - 0.5) < 1e-9
    assert abs(normal_sf(1.96) - 0.025) < 5e-4
    assert normal_sf(4.0) < 5e-5
    assert normal_sf(-1.0) > 0.8


def test_compute_detection_detected_at_threshold() -> None:
    # Large green excess → detected
    result = compute_detection(
        num_tokens_total=80,
        num_tokens_scored=80,
        num_green=50,
        gamma=0.25,
        threshold=4.0,
        min_scored_tokens=20,
    )
    assert result.z_score > 4.0
    assert result.detected
    assert result.verdict == "detected"
    assert "AI" not in result.verdict_label
    assert "confidence" not in result.verdict_label.lower()


def test_short_text_insufficient() -> None:
    result = compute_detection(
        num_tokens_total=10,
        num_tokens_scored=10,
        num_green=8,
        gamma=0.25,
        threshold=4.0,
        min_scored_tokens=20,
    )
    assert result.verdict == "insufficient_scored_tokens"
    assert not result.detected  # UX guardrail even if z is high


def test_portable_prefix_exclusion() -> None:
    wm = InspectableKGW(key=TEACHING_KEY, profile=TEACHING_KGW)
    # h=1 → first token excluded as missing_context
    tokens = [1, 2, 3, 4, 5]
    trace = wm.score_trace(token_ids=tokens, portable=True)
    assert trace.positions[0].exclusion_reason == "missing_context"
    assert not trace.positions[0].eligible
    assert trace.result.excluded_prefix_count >= 1
    assert trace.result.num_tokens_scored == 4


def test_repeated_ngram_excluded_once() -> None:
    wm = InspectableKGW(key=TEACHING_KEY, profile=TEACHING_KGW)
    # With h=1, sequence 7,3,7,3: units (7,3) and (3,7) then (7,3) repeats
    tokens = [7, 3, 7, 3]
    trace = wm.score_trace(token_ids=tokens, portable=True)
    # pos0 missing context; pos1 unit (7,3); pos2 unit (3,7); pos3 unit (7,3) repeated
    reasons = [p.exclusion_reason for p in trace.positions]
    assert reasons[0] == "missing_context"
    assert reasons[1] is None
    assert reasons[2] is None
    assert reasons[3] == "repeated_ngram"
    assert trace.result.excluded_repeated_count == 1
    assert trace.result.num_tokens_scored == 2


def test_wrong_key_scores_near_null_batch() -> None:
    """Loaded text under a wrong key should not stay strongly detected across a batch."""
    engine = FakeEngine(default_length=64, key=TEACHING_KEY)
    wrong = InspectableKGW(key=parse_key_material("wrong-key-material"), profile=TEACHING_KGW)
    z_correct: list[float] = []
    z_wrong: list[float] = []
    for seed in range(6):
        pair = engine.generate_pair_traced("why cities grow shops", seed=seed, length=64)
        ids = pair["loaded"].token_ids
        z_correct.append(engine.watermark.score_tokens(token_ids=ids).z_score)
        z_wrong.append(wrong.score_tokens(token_ids=ids).z_score)
    avg_correct = sum(z_correct) / len(z_correct)
    avg_wrong = sum(z_wrong) / len(z_wrong)
    assert avg_correct > 2.0
    assert avg_wrong < avg_correct - 1.0


def test_verdict_labels_never_claim_ai_authorship() -> None:
    for scored, green in ((0, 0), (10, 8), (50, 12), (50, 40)):
        r = compute_detection(
            num_tokens_total=scored,
            num_tokens_scored=scored,
            num_green=green,
            gamma=0.25,
            threshold=4.0,
        )
        label = r.verdict_label.lower()
        assert "ai-generated" not in label
        assert "ai authorship" not in label
        assert "confidence" not in label
        assert "claude" not in label
