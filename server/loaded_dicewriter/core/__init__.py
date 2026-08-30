"""Core watermark math, profiles, and shared types."""

from loaded_dicewriter.core.keys import (
    TEACHING_KEY,
    key_fingerprint,
    parse_key_material,
)
from loaded_dicewriter.core.prf import green_mask, is_green
from loaded_dicewriter.core.profiles import TEACHING_KGW, WatermarkProfile
from loaded_dicewriter.core.stats import DetectionResult, compute_detection, normal_sf, z_score

__all__ = [
    "TEACHING_KEY",
    "TEACHING_KGW",
    "DetectionResult",
    "WatermarkProfile",
    "compute_detection",
    "green_mask",
    "is_green",
    "key_fingerprint",
    "normal_sf",
    "parse_key_material",
    "z_score",
]
