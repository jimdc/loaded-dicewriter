"""Transformers-path KGW math without downloading model weights."""

from __future__ import annotations

import math

from loaded_dicewriter.core.keys import TEACHING_KEY
from loaded_dicewriter.core.profiles import TEACHING_KGW
from loaded_dicewriter.generation.sampler import softmax
from loaded_dicewriter.inference.transformers_backend import (
    TransformersBackend,
    TransformersConfigError,
    apply_kgw_to_logits,
    bias_logits_python,
    select_device,
)
from loaded_dicewriter.settings import Settings, clear_settings_cache


def test_bias_only_green_tokens() -> None:
    logits = [0.0, 1.0, -1.0, 0.5]
    mask = [True, False, True, False]
    out = bias_logits_python(logits, mask, 2.0)
    assert out == [2.0, 1.0, 1.0, 0.5]


def test_apply_kgw_deterministic() -> None:
    logits = [math.log(i + 1) for i in range(32)]
    a, mask_a = apply_kgw_to_logits(
        logits=logits,
        context_ids=[3],
        key=TEACHING_KEY,
        profile=TEACHING_KGW,
    )
    b, mask_b = apply_kgw_to_logits(
        logits=logits,
        context_ids=[3],
        key=TEACHING_KEY,
        profile=TEACHING_KGW,
    )
    assert a == b
    assert mask_a == mask_b
    assert any(mask_a)
    # Probabilities still normalize.
    probs = softmax(a)
    assert abs(sum(probs) - 1.0) < 1e-9


def test_from_settings_requires_local_path(monkeypatch: object) -> None:
    clear_settings_cache()
    settings = Settings()
    # Default is fake mode.
    try:
        TransformersBackend.from_settings(settings)
        raised = False
    except TransformersConfigError:
        raised = True
    assert raised

    settings = Settings.model_validate(
        {
            "model": {"mode": "transformers", "model_path": None},
        }
    )
    try:
        TransformersBackend.from_settings(settings)
        raised = False
    except TransformersConfigError as exc:
        raised = True
        assert "model_path" in str(exc)
    assert raised


def test_from_settings_missing_path_errors() -> None:
    settings = Settings.model_validate(
        {
            "model": {
                "mode": "transformers",
                "model_path": "/nonexistent/path/to/model",
            },
        }
    )
    try:
        TransformersBackend.from_settings(settings)
        raise AssertionError("expected TransformersConfigError")
    except TransformersConfigError as exc:
        assert "does not exist" in str(exc)


def test_select_device_returns_string() -> None:
    dev = select_device()
    assert dev in {"cpu", "cuda", "mps"}
