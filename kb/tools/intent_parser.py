"""
Intent Parser (Phase 5 — VideoAgent pattern).

Decomposes a user request into explicit + implicit intents (VideoAgent pattern).
Explicit intents are what the user literally asked for. Implicit intents are
inferred from the content type + signals (e.g., "make it funny" implicit in
a comedy vlog; "add hooks" implicit in a social-short).

Public surface:
  - parse_intents(user_request, content_type, source_profile) -> dict
    Returns {"explicit": [...], "implicit": [...], "all": [...]}
"""
from __future__ import annotations

import typing as t


# Implicit intents inferred per content type (from RESEARCH-3 VideoAgent pattern)
IMPLICIT_INTENTS_BY_CONTENT_TYPE: dict[str, list[str]] = {
    "vlog": [
        "maintain pattern interrupt every 5-10s",
        "hook viewer in first 1.5s",
        "preserve emotional peaks",
        "duck music under speech",
    ],
    "social-short": [
        "hook in first 1.5s with verbal+visual interrupt",
        "maintain pattern interrupt every 3-5s",
        "vertical 9:16 framing",
        "aggressive pacing (-14 LUFS)",
        "kinetic text captions",
    ],
    "short_form": [  # alias for social-short
        "hook in first 1.5s with verbal+visual interrupt",
        "maintain pattern interrupt every 3-5s",
        "vertical 9:16 framing",
        "aggressive pacing (-14 LUFS)",
        "kinetic text captions",
    ],
    "podcast": [
        "remove silences and filler words",
        "extract 3 best moments as shorts",
        "add chapter markers",
        "level audio to -16 LUFS",
    ],
    "tutorial": [
        "sync screen + face PiP",
        "add chapter markers at topic changes",
        "ensure clear VO at -16 LUFS",
        "highlight on-screen text via OCR",
    ],
    "cinematic": [
        "color grade in known working space (ACEScg/Rec.709)",
        "wide dynamic range (-23 LUFS)",
        "use slow pacing (8-15s shots)",
        "apply LUTs for look",
    ],
    "documentary": [
        "transcript-first editing with J/L-cuts (0.5-1.5s)",
        "B-roll overlay on talking head",
        "narrative coherence across segments",
        "music bed ducked under narration",
    ],
    "interview": [
        "multi-cam speaker switching",
        "J/L-cuts at 0.2-0.5s",
        "speaker labels",
        "level audio to -16 LUFS",
    ],
    "talking-head": [
        "remove silences",
        "dynamic zoom on emphasis",
        "warm color grade",
        "subtitles (max 2 lines, 42 chars)",
    ],
    "music-video": [
        "beat-aligned cuts (Δt ≤ 0.1s)",
        "section-anchored structure",
        "energetic pacing (-14 LUFS)",
        "visual sync to music energy",
    ],
    "event": [
        "highlight key moments (vows, toasts, action)",
        "music bed with ducking",
        "cinematic color grade",
        "2-4 minute output",
    ],
}

# Explicit intent keywords (rule-based extraction from user request text)
EXPLICIT_KEYWORDS: dict[str, list[str]] = {
    "extract highlights": ["highlight", "best moments", "best parts", "key moments"],
    "remove silence": ["silence", "pause", "dead air", "um", "filler"],
    "add subtitles": ["subtitle", "caption", "srt", "cc"],
    "color grade": ["color", "grade", "lut", "cinematic look", "warm", "cool"],
    "add music": ["music", "soundtrack", "bed", "background audio"],
    "vertical reframe": ["vertical", "9:16", "tiktok", "reels", "shorts"],
    "slow motion": ["slow mo", "slow motion", "speed ramp", "velocity"],
    "fast pace": ["fast", "punchy", "quick cuts", "energetic"],
    "add transitions": ["transition", "fade", "whip", "zoom"],
    "add B-roll": ["b-roll", "broll", "overlay", "cutaway"],
    "chapter markers": ["chapter", "segment", "section marker"],
    "multi-cam": ["multi-cam", "multicam", "camera switch"],
    "comedy/funny": ["funny", "comedy", "humor", "joke"],
    "emotional": ["emotional", "heartfelt", "touching", "moving"],
    "dramatic": ["dramatic", "intense", "epic", "cinematic"],
}


def parse_intents(user_request: str = "", content_type: str = "vlog",
                  source_profile: t.Optional[dict] = None) -> dict:
    """
    Decompose a user request into explicit + implicit intents.

    Args:
        user_request: natural-language request (may be empty if only recipe YAML given)
        content_type: drives implicit intents
        source_profile: optional, used to refine implicit intents (e.g., if no audio, skip audio intents)

    Returns: {"explicit": [...], "implicit": [...], "all": [...]}
    """
    explicit: list[str] = []
    request_lower = (user_request or "").lower()

    # Extract explicit intents via keyword matching
    for intent, keywords in EXPLICIT_KEYWORDS.items():
        if any(kw in request_lower for kw in keywords):
            explicit.append(intent)

    # Implicit intents from content type
    implicit = list(IMPLICIT_INTENTS_BY_CONTENT_TYPE.get(content_type, []))

    # Refine implicit based on source profile
    if source_profile:
        meta = source_profile.get("metadata", {})
        if not meta.get("has_audio", True):
            # No audio — remove audio-related implicit intents
            implicit = [i for i in implicit if "LUFS" not in i and "audio" not in i.lower() and "music" not in i.lower() and "speech" not in i.lower()]
        audio = source_profile.get("audio", {})
        if audio.get("tempo", 0) == 0:
            # No music detected — remove beat-aligned intents
            implicit = [i for i in implicit if "beat" not in i.lower()]

    # Deduplicate while preserving order
    seen: set[str] = set()
    all_intents: list[str] = []
    for i in explicit + implicit:
        if i not in seen:
            seen.add(i)
            all_intents.append(i)

    return {
        "explicit": explicit,
        "implicit": implicit,
        "all": all_intents,
    }
