"""
Single source of truth for content types across the entire framework.

All content type strings used by classifier.py, pacing_engine.py, recipe YAMLs,
reviewer.py, intent_parser.py, and recipe_runner.py MUST come from this module.

This eliminates the "short_form vs social-short" naming mismatch class of bug
permanently — the enum is the one place that defines valid names.
"""
from __future__ import annotations

import enum


class ContentType(str, enum.Enum):
    """All valid content types. The string values are what appears in recipe YAMLs."""
    VLOG = "vlog"
    SOCIAL_SHORT = "social-short"
    SHORT_FORM = "short_form"  # alias for social-short (used in recipe YAMLs)
    PODCAST = "podcast"
    TUTORIAL = "tutorial"
    CINEMATIC = "cinematic"
    DOCUMENTARY = "documentary"
    INTERVIEW = "interview"
    TALKING_HEAD = "talking-head"
    MUSIC_VIDEO = "music-video"
    EVENT = "event"

    @classmethod
    def all_values(cls) -> list[str]:
        """Return all valid content type string values."""
        return [e.value for e in cls]

    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Check if a string is a valid content type."""
        return value in cls.all_values()

    @classmethod
    def normalize(cls, value: str) -> str:
        """Normalize a content type to its canonical form.
        short_form → social-short (they're the same thing).
        If already valid, returns as-is. If invalid, returns 'vlog' (safe default)."""
        if not value:
            return "vlog"
        if value == "short_form":
            return "social-short"
        if cls.is_valid(value):
            return value
        return "vlog"

    @classmethod
    def for_pacing(cls, value: str) -> str:
        """Return the content type as it should appear in PACING_PROFILES.
        Both 'short_form' and 'social-short' map to 'social-short' in pacing.
        This is the single place that resolves the alias."""
        return cls.normalize(value)


# Convenience set for imports
ALL_CONTENT_TYPES = ContentType.all_values()
