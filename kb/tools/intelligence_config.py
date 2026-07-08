"""
Centralized configuration for all intelligence-layer tuning constants.

Every magic number in relevance_map.py, hero_detector.py, slowmo_engine.py,
and pacing_engine.py should reference this config instead of hardcoding values.

This is the single place to tune the entire intelligence layer —
adjust thresholds here, and every module that imports it picks up the change.

Phase 3 of the upgrade plan.
"""
from __future__ import annotations

import dataclasses
import typing as t


@dataclasses.dataclass(frozen=True)
class IntelligenceConfig:
    """All tuning constants for the intelligence layer.

    Adjust these values to tune the system. One instance per content type
    (or use the DEFAULT config for all content types)."""

    # ── Relevance Map (relevance_map.py) ──
    hero_threshold: float = 0.5
    """Minimum hero_score for a window to be a hero moment."""
    dead_zone_threshold: float = 0.20
    """Maximum score (all dims below) for a window to be a dead zone."""
    adaptive_dead_zone: bool = True
    """If True, lower dead_zone_threshold when max_hero_score < 0.3."""
    dead_zone_min_duration: int = 3
    """Minimum consecutive seconds to flag as a dead zone."""

    # ── Hero Detector (hero_detector.py) ──
    co_occurrence_window: float = 0.8
    """Seconds within which peaks from different modalities must co-occur."""

    # ── Slow-Mo Engine (slowmo_engine.py) ──
    motion_sigma_threshold: float = 2.0
    """Minimum sigma for a motion peak to be considered for slow-mo."""
    motion_only_threshold: float = 2.5
    """Sigma above which slow-mo is proposed even without audio onset."""
    slowmo_co_occurrence_window: float = 0.8
    """Seconds within which audio onset must co-occur with motion peak."""
    max_slowmo_per_minute: int = 3
    """Maximum slow-mo proposals per minute of video."""

    # ── Cut Detector (cut_detector.py) ──
    min_cut_score: float = 0.55
    """Minimum Murch composite score for a cut point to be returned."""
    beat_tolerance: float = 0.15
    """Seconds tolerance for snapping cuts to beats."""
    section_tolerance: float = 1.0
    """Seconds tolerance for snapping cuts to music section boundaries."""

    # ── Probe Layer (probe.py, probe_visual.py, probe_audio.py) ──
    motion_sample_stride: int = 3
    """Sample every Nth frame for motion energy (2 = every 2nd frame)."""
    aesthetic_sample_interval: float = 6.0
    """Sample one frame every N seconds for aesthetic scoring."""
    face_sample_stride: int = 8
    """Sample every Nth frame for face/emotion detection."""

    # ── Speech Detection Gate (probe_semantic.py) ──
    speech_cv_threshold: float = 0.12
    """Coefficient of variation below which audio is considered non-speech."""


# Default config (used by all content types unless overridden)
DEFAULT = IntelligenceConfig()

# Per-content-type overrides (extend as needed)
_OVERRIDES: dict[str, IntelligenceConfig] = {
    "social-short": IntelligenceConfig(
        hero_threshold=0.5,
        dead_zone_threshold=0.20,
        max_slowmo_per_minute=3,
    ),
    "cinematic": IntelligenceConfig(
        hero_threshold=0.7,
        dead_zone_threshold=0.30,
        max_slowmo_per_minute=1,
    ),
    "vehicle-action": IntelligenceConfig(
        hero_threshold=0.45,
        dead_zone_threshold=0.18,
        max_slowmo_per_minute=4,
        motion_only_threshold=2.0,
    ),
    "podcast": IntelligenceConfig(
        hero_threshold=0.65,
        dead_zone_threshold=0.20,
        max_slowmo_per_minute=0,  # no slow-mo for podcasts
    ),
}


def get_config(content_type: str = "vlog") -> IntelligenceConfig:
    """Get the IntelligenceConfig for a content type.
    Falls back to DEFAULT if no override exists."""
    from kb.tools.content_types import ContentType
    normalized = ContentType.normalize(content_type)
    return _OVERRIDES.get(normalized, DEFAULT)
