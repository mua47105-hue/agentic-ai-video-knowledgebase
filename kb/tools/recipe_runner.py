"""
Recipe runner: execute YAML recipe packs against input video files.

Usage:
    python3 -m kb.tools.recipe_runner recipes/podcast-to-shorts.yaml input.mp4 --output shorts/
    python3 -m kb.tools.recipe_runner recipes/wedding-highlights.yaml input.mp4

Schema:
    Each recipe is a YAML file with:
      - metadata (name, version, content_type, target_platform, output_lufs)
      - steps: ordered list of operations
      - quality_gates: post-execution checks
      - for_each_segment: parallel loop construct (loop_var, source, steps)
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import typing as t
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

try:
    from kb.tools.classifier import classify_video, recommend_recipe
except ImportError:
    classify_video = None  # type: ignore
    recommend_recipe = None  # type: ignore

try:
    from kb.tools.auto_recover import RecoveryEngine, RecoveryResult
except ImportError:
    RecoveryEngine = None  # type: ignore
    RecoveryResult = None  # type: ignore

try:
    from kb.tools.decision_log import DecisionLogger
except ImportError:
    DecisionLogger = None  # type: ignore

# Phase 6-9 intelligence layer (all optional — graceful degradation)
try:
    from kb.tools.probe import probe_video as _probe_video
except ImportError:
    _probe_video = None  # type: ignore

try:
    from kb.tools.profile_cache import get_or_probe as _get_or_probe, get_cached_profile as _get_cached_profile
except ImportError:
    _get_or_probe = None  # type: ignore
    _get_cached_profile = None  # type: ignore

try:
    from kb.tools.relevance_map import build_relevance_map as _build_relevance_map
except ImportError:
    _build_relevance_map = None  # type: ignore

try:
    from kb.tools.cut_detector import find_best_cuts as _find_best_cuts
except ImportError:
    _find_best_cuts = None  # type: ignore

try:
    from kb.tools.pacing_engine import build_paced_plan as _build_paced_plan
except ImportError:
    _build_paced_plan = None  # type: ignore

try:
    from kb.tools.slowmo_engine import find_slowmo_moments as _find_slowmo_moments
except ImportError:
    _find_slowmo_moments = None  # type: ignore

try:
    from kb.tools.music_sync import build_music_sync_plan as _build_music_sync_plan
except ImportError:
    _build_music_sync_plan = None  # type: ignore

try:
    from kb.tools.hero_detector import detect_hero_moments as _detect_hero_moments
except ImportError:
    _detect_hero_moments = None  # type: ignore

try:
    from kb.tools.intelligent_planner import generate_plan as _generate_plan
except ImportError:
    _generate_plan = None  # type: ignore

try:
    from kb.tools.reviewer import review_output as _review_output
except ImportError:
    _review_output = None  # type: ignore

try:
    from kb.tools.edit_memory import EditPatternDB as _EditPatternDB
except ImportError:
    _EditPatternDB = None  # type: ignore

# Phase 5 intelligence architecture additions
try:
    from kb.tools.llm_router import get_router as _get_router
except ImportError:
    _get_router = None  # type: ignore

try:
    from kb.tools.artifact_store import ArtifactStore as _ArtifactStore
except ImportError:
    _ArtifactStore = None  # type: ignore

try:
    from kb.tools.intent_parser import parse_intents as _parse_intents
except ImportError:
    _parse_intents = None  # type: ignore

try:
    from kb.tools.editing_research import research_edit as _research_edit
except ImportError:
    _research_edit = None  # type: ignore

try:
    from kb.tools.build_orchestrator import orchest_build as _orchest_build
except ImportError:
    _orchest_build = None  # type: ignore

try:
    from kb.tools.auto_recover import parse_retry_if_from_yaml as _parse_retry_if
except ImportError:
    _parse_retry_if = None  # type: ignore


class RecipeSubstitutionError(Exception):
    """Raised when a $variable substitution in a recipe cannot be resolved cleanly."""
    pass


# ── Platform preset pack (Section 7) ──

PLATFORM_SPECS: dict[str, dict] = {
    "tiktok": {
        "safe_w": 900, "safe_h": 1400,
        "margin_v": 350, "margin_r": 130,
        "duration_min": 21, "duration_max": 34,
        "loudness_lufs": -14,
    },
    "instagram": {
        "safe_w": 900, "safe_h": 1400,
        "margin_v": 400, "margin_r": 0,
        "duration_min": 11, "duration_max": 17,
        "loudness_lufs": -14,
    },
    "youtube_shorts": {
        "safe_w": 900, "safe_h": 1400,
        "margin_v": 400, "margin_r": 0,
        "duration_min": 30, "duration_max": 50,
        "loudness_lufs": -14,
    },
}


# ── Pacing/rhythm presets (Section 8) ──

PACING_PRESETS: dict[str, dict] = {
    "punchy_shorts": {
        "hook_window": (0, 2),
        "cut_cadence": (2, 4),
        "pattern_interrupt": (5, 8),
        "min_segment_duration": 2,
        "max_segment_duration": 6,
        "max_candidates": 8,
        "description": "TikTok/Reels: hard hook in 0–2s, cuts every 2–4s, zoom/SFX every 5–8s",
    },
    "steady_tutorial": {
        "hook_window": (0, 5),
        "cut_cadence": (5, 8),
        "pattern_interrupt": (10, 15),
        "min_segment_duration": 5,
        "max_segment_duration": 12,
        "max_candidates": 15,
        "description": "Tutorial/documentary: promise in 0–5s, cuts every 5–8s, gentle pacing",
    },
    "broadcast_calm": {
        "hook_window": None,
        "cut_cadence": None,
        "pattern_interrupt": None,
        "min_segment_duration": 8,
        "max_segment_duration": 20,
        "max_candidates": 20,
        "description": "Broadcast/compliance: editorial pacing, no forced cadence",
    },
}

EMPHASIS_WORDS: set[str] = {
    "top", "best", "worst", "never", "always", "most", "only", "ever",
    "but", "actually", "turns", "out", "literally", "finally",
    "one", "two", "three", "first", "second", "last", "new", "big",
    "huge", "massive", "incredible", "amazing", "terrible", "secret",
    "you", "your", "because", "so", "here", "watch", "look", "try",
    "free", "now", "today", "right", "number", "how", "why",
    "what", "when", "does", "don't", "do", "will", "can",
}


# ── Variable substitution ──

def _substitute(value: t.Any, context: dict) -> t.Any:
    if isinstance(value, str):
        def _replace_var(m: re.Match) -> str:
            path = m.group(1).strip()
            parts = path.split(".")
            cur = context
            for p in parts:
                if isinstance(cur, dict):
                    cur = cur.get(p, "")
                elif isinstance(cur, list):
                    try:
                        idx = int(p)
                        cur = cur[idx] if 0 <= idx < len(cur) else ""
                    except (ValueError, IndexError):
                        cur = ""
                else:
                    cur = ""
            if cur is None:
                return ""
            if isinstance(cur, dict):
                if "path" in cur:
                    return str(cur["path"])
                raise RecipeSubstitutionError(
                    f"$var '{path}' resolved to a dict without a 'path' key. "
                    f"Available keys: {list(cur.keys())}. Either use '$.{path}.path' or "
                    f"ensure the upstream step produces a 'path' field."
                )
            if isinstance(cur, list):
                raise RecipeSubstitutionError(
                    f"$var '{path}' resolved to a list (len {len(cur)}). "
                    f"Did you forget an index? E.g. '${path}.0'"
                )
            return str(cur)
        return re.sub(r"\$([\w.]+)", _replace_var, value)
    elif isinstance(value, dict):
        return {k: _substitute(v, context) for k, v in value.items()}
    elif isinstance(value, list):
        return [_substitute(v, context) for v in value]
    return value


# ── Tool resolver ──

_TOOL_CACHE: dict[str, t.Callable] = {}


def _resolve_tool(tool_name: str) -> t.Callable:
    if tool_name in _TOOL_CACHE:
        return _TOOL_CACHE[tool_name]

    if tool_name.startswith("edit."):
        from kb.tools.unified_adapter import edit
        fn = getattr(edit, tool_name[5:], None)
    elif tool_name.startswith("music."):
        from kb.tools.unified_adapter import music
        fn = getattr(music, tool_name[6:], None)
    elif tool_name == "recipe.find_engaging_segments":
        fn = _find_engaging_segments
    elif tool_name == "recipe.find_key_moments":
        fn = _find_key_moments
    elif tool_name == "recipe.find_action_moments":
        fn = _find_action_moments
    elif tool_name == "recipe.segment_by_topic":
        fn = _segment_by_topic
    elif tool_name == "recipe.find_best_shots":
        fn = _find_best_shots
    elif tool_name == "recipe.speed_ramp":
        fn = _speed_ramp
    elif tool_name == "recipe.snap_to_beats":
        fn = snap_to_beats
    elif tool_name == "recipe.remove_filler_words":
        fn = remove_filler_words
    else:
        raise ValueError(f"unknown tool: {tool_name}")

    _TOOL_CACHE[tool_name] = fn
    return fn


def _call_tool(tool_name: str, params: dict, *, context: dict | None = None) -> t.Any:
    fn = _resolve_tool(tool_name)
    # Pass context to functions that accept it (the recipe.find_* family)
    if context is not None and _accepts_context(fn):
        try:
            return fn(context=context, **params)
        except TypeError as e:
            raise TypeError(f"tool {tool_name}({list(params)}): {e}")
    try:
        return fn(**params)
    except TypeError as e:
        raise TypeError(f"tool {tool_name}({list(params)}): {e}")


def _accepts_context(fn: t.Callable) -> bool:
    """Check if a function accepts a 'context' keyword argument."""
    import inspect
    try:
        sig = inspect.signature(fn)
        return "context" in sig.parameters or any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
        )
    except (ValueError, TypeError):
        return False


def _recipe_needs_intelligence(steps: list[dict]) -> bool:
    """Speed: determine if a recipe actually uses intelligence-layer outputs.
    If it only calls edit.trim/resize/render/color_grade (no find_* tools, no
    for_each loops that consume segments), the probe is wasted work — skip it."""
    if not steps:
        return False
    for step in steps:
        tool = step.get("tool", "")
        op = step.get("operation", "")
        # recipe.find_* tools consume _paced_plan/_hero_moments → need probe
        if tool.startswith("recipe.find_") or tool.startswith("recipe.segment_by_topic"):
            return True
        # for_each loops consume segment_list/chapters/shots → likely from find_*
        if op.startswith("for_each_"):
            return True
        # If recipe declares verify_moments, it needs the probe for VLM
        if step.get("verify_moments"):
            return True
        # Recurse into loop sub-steps
        if op.startswith("for_each_") and step.get("steps"):
            if _recipe_needs_intelligence(step["steps"]):
                return True
    return False


# ── Built-in recipe tools ──

def _find_engaging_segments(
    transcript: dict,
    chapters: list[dict] | None = None,
    *,
    min_duration: float = 30,
    max_duration: float = 60,
    criteria: list[str] | None = None,
    target_platform: str = "",
    pacing: str = "",
    context: dict | None = None,
) -> list[dict]:
    """Find engaging segments using multi-signal scoring (Section 4).

    Scoring signals (all optional, weighted sum):
      1. Speech-rate variance (needs word timestamps)
      2. Curiosity/hook keyword density
      3. Word-count baseline (existing heuristic — fallback)

    When target_platform or pacing is set, min/max defaults pull
    from PLATFORM_SPECS / PACING_PRESETS.

    Phase 5 wiring: if context has _paced_plan (from Phase 8 pacing engine),
    use kept segments as the PRIMARY signal — they're scored by the multimodal
    relevance map + Murch cut detector, far richer than transcript-only heuristics.
    Falls back to transcript-only scoring only when the intelligence layer didn't run.
    """
    # Phase 5: Intelligence layer first — use paced_plan kept segments if available
    if context is not None:
        paced = context.get("_paced_plan")
        if paced and paced.get("segments"):
            kept = [s for s in paced["segments"] if s.get("keep", True)
                    and min_duration <= (s["end"] - s["start"]) <= max_duration]
            if kept:
                # Map paced_plan segment shape → find_engaging_segments return shape
                result = [{
                    "start": s["start"],
                    "duration": s["end"] - s["start"],
                    "label": s.get("reason", "paced_segment"),
                    "score": s.get("pacing_score", 0.7),
                    "source": "intelligence_layer",
                } for s in kept]
                # Sort by pacing_score descending, cap at max_candidates
                result.sort(key=lambda c: c.get("score", 0), reverse=True)
                max_candidates = 5
                if pacing and pacing in PACING_PRESETS:
                    max_candidates = PACING_PRESETS[pacing]["max_candidates"]
                return result[:max_candidates]

    # Fallback: transcript-only heuristic (original behavior)
    if target_platform and target_platform in PLATFORM_SPECS:
        ps = PLATFORM_SPECS[target_platform]
        min_duration = ps["duration_min"]
        max_duration = ps["duration_max"]

    if pacing and pacing in PACING_PRESETS:
        pp = PACING_PRESETS[pacing]
        min_duration = pp["min_segment_duration"]
        max_duration = pp["max_segment_duration"]

    segs = transcript.get("segments", []) if transcript else []
    words = transcript.get("words", []) if transcript else []
    if not segs:
        return [{"start": 0, "duration": max_duration, "label": "full"}]

    candidates: list[dict] = []
    for s in segs:
        dur = s.get("end", 0) - s.get("start", 0)
        if min_duration <= dur <= max_duration:
            text = s.get("text", "")
            if not text:
                continue

            seg_words = s.get("words", [])
            score = _segment_score(text, seg_words)
            candidates.append({
                "start": s["start"],
                "duration": dur,
                "label": text[:60],
                "score": score,
                "text": text,
                "source": "transcript_heuristic",
            })

    candidates.sort(key=lambda c: c["score"], reverse=True)
    max_candidates = 5
    if pacing and pacing in PACING_PRESETS:
        max_candidates = PACING_PRESETS[pacing]["max_candidates"]
    return candidates[:max_candidates] if candidates else [{"start": 0, "duration": max_duration, "label": "clip"}]


def _segment_score(text: str, seg_words: list[dict]) -> float:
    """Weighted multi-signal score for a single segment.

    Returns 0.0–10.0 score where higher = more engaging.
    """
    if not text.strip():
        return 0.0
    word_count = len(text.strip().split())
    base = min(word_count / 10.0, 5.0)

    # Signal 1: keyword/heuristic density
    words_lower = text.lower().split()
    keyword_hits = sum(1 for w in words_lower if w.strip(".,!?") in EMPHASIS_WORDS)
    keyword_score = min(keyword_hits / max(word_count, 1) * 20, 3.0)

    # Signal 2: speech-rate variance (from word timestamps)
    rate_score = 0.0
    if len(seg_words) >= 3:
        rates: list[float] = []
        for i in range(1, len(seg_words)):
            gap = seg_words[i]["start"] - seg_words[i - 1]["end"]
            dur = seg_words[i]["end"] - seg_words[i]["start"]
            if dur > 0:
                rates.append(1.0 / max(dur, 0.01))
        if rates:
            mean_rate = sum(rates) / len(rates)
            variance = sum((r - mean_rate) ** 2 for r in rates) / len(rates)
            rate_score = min(variance * 2, 2.0)

    return base + keyword_score + rate_score


def _find_key_moments(
    transcript: dict,
    scenes: list[dict] | None = None,
    *,
    categories: list[str] | None = None,
    max_duration_per_moment: float = 45,
    context: dict | None = None,
) -> list[dict]:
    """Phase 5 wiring: if context has _hero_moments (from Phase 9 cross-modal
    hero detector), use those as the PRIMARY signal — they fuse audio + visual +
    semantic peaks. Falls back to transcript segment extraction when the
    intelligence layer didn't run."""
    # Intelligence layer first: cross-modal hero moments
    if context is not None:
        heroes = context.get("_hero_moments")
        if heroes:
            result = []
            for h in heroes:
                if h.get("level", 0) >= 2:  # level 2+ = double or triple co-occurrence
                    dur = h["end"] - h["start"]
                    result.append({
                        "start": h["start"],
                        "duration": min(dur, max_duration_per_moment),
                        "label": f"{h.get('label', 'hero')}_{h.get('level', 0)}",
                        "score": h.get("geometric_mean", 0.5),
                        "source": "intelligence_layer",
                        "reasoning": h.get("fusion_reasoning", "")[:100],
                    })
            if result:
                result.sort(key=lambda c: c.get("score", 0), reverse=True)
                return result[:10]
    # Fallback: transcript-based extraction
    if transcript:
        segs = transcript.get("segments", [])
        return [{"start": s["start"], "duration": min(s["end"] - s["start"], max_duration_per_moment), "label": s.get("text", "")[:40]} for s in segs[:10]]
    return [{"start": 0, "duration": max_duration_per_moment, "label": "moment"}]


def _find_action_moments(
    scenes: list[dict] | None = None,
    *,
    min_duration: float = 3,
    max_duration: float = 15,
    min_energy_threshold: float = 0.6,
    context: dict | None = None,
) -> list[dict]:
    """Phase 5 wiring: if context has _hero_moments with level ≥ 2 (cross-modal
    peak co-occurrence), use those as the PRIMARY signal for action moments —
    they're where motion energy + audio onset + semantic salience all peak.
    Also checks _slowmo_proposals (impact type) as a secondary intelligence signal.
    Falls back to scene-boundary extraction when the intelligence layer didn't run."""
    # Intelligence layer first: hero moments + slow-mo impact proposals
    if context is not None:
        heroes = context.get("_hero_moments") or []
        slowmo = context.get("_slowmo_proposals") or []
        intel_moments = []
        # Hero moments with high motion (impact-type)
        for h in heroes:
            if h.get("level", 0) >= 2:
                dur = h["end"] - h["start"]
                if min_duration <= dur <= max_duration:
                    intel_moments.append({
                        "start": h["start"],
                        "duration": dur,
                        "label": f"hero_{h.get('level', 0)}",
                        "source": "intelligence_layer",
                        "score": h.get("geometric_mean", 0.5),
                    })
        # Slow-mo impact proposals (motion spike + audio onset)
        for p in slowmo:
            if p.get("moment_type") == "impact":
                dur = p.get("duration", 0)
                if min_duration <= dur <= max_duration:
                    intel_moments.append({
                        "start": p["start"],
                        "duration": dur,
                        "label": "impact_slowmo",
                        "source": "intelligence_layer",
                        "score": 0.9,
                    })
        if intel_moments:
            intel_moments.sort(key=lambda c: c.get("score", 0), reverse=True)
            return intel_moments[:15]
    # Fallback: scene-boundary extraction
    if not scenes:
        return [{"start": 0, "duration": max_duration, "label": "action"}]
    candidates = []
    for i, s in enumerate(scenes):
        t = s.get("timestamp", 0)
        dur = max_duration
        if i + 1 < len(scenes):
            dur = min(scenes[i + 1].get("timestamp", t + max_duration) - t, max_duration)
        if dur >= min_duration:
            candidates.append({"start": t, "duration": dur, "label": f"action_{i}", "source": "scene_heuristic"})
    return candidates[:15] if candidates else [{"start": 0, "duration": max_duration, "label": "action"}]


def _segment_by_topic(
    transcript: dict,
    *,
    min_segment_duration: float = 30,
    max_segment_duration: float = 180,
) -> list[dict]:
    segs = transcript.get("segments", [])
    if not segs:
        return [{"start": 0, "duration": max_segment_duration, "label": "full"}]
    chunks: list[dict] = []
    current_start = segs[0]["start"]
    current_text = ""
    for s in segs:
        dur = s["end"] - current_start
        if dur >= max_segment_duration:
            chunks.append({"start": current_start, "duration": dur, "label": current_text[:60]})
            current_start = s["start"]
            current_text = ""
        current_text += " " + s.get("text", "")
    if current_text:
        dur = segs[-1]["end"] - current_start
        if dur >= min_segment_duration:
            chunks.append({"start": current_start, "duration": dur, "label": current_text[:60]})
    return chunks if chunks else [{"start": 0, "duration": max_segment_duration, "label": "full"}]


def _find_best_shots(
    scenes: list[dict] | None = None,
    *,
    max_clips: int = 20,
    min_duration: float = 3,
    max_duration: float = 12,
) -> list[dict]:
    if not scenes:
        return [{"start": 0, "duration": max_duration, "label": "shot"}]
    candidates = []
    for i, s in enumerate(scenes):
        t = s.get("timestamp", 0)
        dur = max_duration
        if i + 1 < len(scenes):
            dur = min(scenes[i + 1].get("timestamp", t + max_duration) - t, max_duration)
        if dur >= min_duration:
            candidates.append({"start": t, "duration": dur, "label": f"shot_{i}"})
    return candidates[:max_clips] if candidates else [{"start": 0, "duration": max_duration, "label": "shot"}]


def _speed_ramp(
    input: str,
    output: str,
    *,
    pre_roll: float = 0.5,
    pre_speed: float = 0.5,
    impact_speed: float = 1.0,
    post_roll: float = 1.0,
    post_speed: float = 0.35,
) -> str:
    from kb.tools.ffmpeg_adapter import _run, _check_ffmpeg, _ensure_parent
    _check_ffmpeg()
    _ensure_parent(output)
    total = pre_roll + 0.5 + post_roll
    cmd = [
        "ffmpeg", "-i", input,
        "-filter_complex",
        (
            f"[0:v]trim=0:{pre_roll},setpts={1/pre_speed}*PTS[v0];"
            f"[0:v]trim={pre_roll}:{pre_roll+0.5},setpts={1/impact_speed}*PTS[v1];"
            f"[0:v]trim={pre_roll+0.5}:{total},setpts={1/post_speed}*PTS[v2];"
            f"[v0][v1][v2]concat=n=3:v=1:a=0[v];"
            f"[0:a]atrim=0:{pre_roll},atempo={pre_speed}[a0];"
            f"[0:a]atrim={pre_roll}:{pre_roll+0.5},atempo={impact_speed}[a1];"
            f"[0:a]atrim={pre_roll+0.5}:{total},atempo={post_speed}[a2];"
            f"[a0][a1][a2]concat=n=3:v=0:a=1[a]"
        ),
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-c:a", "aac", output,
    ]
    _run(cmd, check=True)
    return output


def snap_to_beats(
    segment_list: list[dict],
    beat_grid: dict,
    *,
    snap_tolerance: float = 0.15,
    prefer_downbeats: bool = True,
) -> list[dict]:
    """Nudge segment start/end to nearest beat within tolerance (Section 3).

    Parameters
    ----------
    segment_list : list[dict]
        Each segment must have ``start`` and ``duration`` keys.
    beat_grid : dict
        Output of ``music.describe()`` — must contain ``beats`` and optionally ``downbeats``.
    snap_tolerance : float
        Max seconds to shift a cut to land on a beat.
    prefer_downbeats : bool
        When both a downbeat and regular beat are in range, prefer the downbeat.

    Returns
    -------
    list[dict]
        Updated segment list with ``start`` and ``duration`` nudged.
        Segments unchanged if no beat within tolerance.
    """
    beats: list[float] = beat_grid.get("beats", [])
    downbeats: list[float] = beat_grid.get("downbeats", [])
    if not beats:
        return segment_list

    def _nearest_beat(t: float) -> float | None:
        candidates: list[tuple[float, float]] = []
        for b in beats:
            if abs(b - t) <= snap_tolerance:
                candidates.append((b, abs(b - t)))
        if not candidates:
            return None

        tie_beats: list[float] = [b for b, d in candidates if d == min(d for _, d in candidates)]
        if prefer_downbeats and len(tie_beats) > 1:
            down_in_range = [b for b in tie_beats if b in downbeats]
            if down_in_range:
                return down_in_range[0]
        return tie_beats[0]

    updated: list[dict] = []
    for seg in segment_list:
        new_seg = dict(seg)
        orig_start = seg["start"]
        orig_end = orig_start + seg["duration"]

        new_start = _nearest_beat(orig_start)
        new_end = _nearest_beat(orig_end)

        if new_start is not None:
            new_seg["start"] = new_start
            new_seg["duration"] = (orig_end if new_end is None else new_end) - new_start
            if new_seg.get("_orig_start") is None:
                new_seg["_orig_start"] = orig_start
        if new_end is not None and new_start is not None:
            new_seg["duration"] = new_end - new_start

        if new_start is None and new_end is not None:
            new_seg["start"] = orig_start
            new_seg["duration"] = new_end - orig_start

        if new_seg["duration"] <= 0:
            raise ValueError(
                f"snap_to_beats produced non-positive duration {new_seg['duration']:.3f}s "
                f"(start={new_seg['start']}, end={orig_end}). "
                f"Beat grid may be misaligned with content."
            )

        updated.append(new_seg)

    return updated


def remove_filler_words(
    input: str,
    output: str,
    words: list[dict],
    *,
    filler_list: list[str] | None = None,
    min_gap: float = 0.15,
) -> str:
    """Remove verbal filler words ("um", "uh", "like") from audio (Section 6).

    Uses word-level timestamps to identify and remove filler segments,
    then re-encodes via the same concat-safe pattern as silence_remove.

    Parameters
    ----------
    input : str
        Path to input video/audio.
    output : str
        Path to output file.
    words : list[dict]
        Word-level timestamps from transcribe() — each must have
        ``word``, ``start``, ``end``.
    filler_list : list[str] | None
        Words to remove. Defaults to common English filler words.
    min_gap : float
        Don't cut fillers closer together than this to avoid choppy micro-cuts.

    Returns
    -------
    str
        Path to output file.
    """
    from kb.tools.ffmpeg_adapter import _run, _check_ffmpeg, _ensure_parent
    _check_ffmpeg()
    _ensure_parent(output)

    if filler_list is None:
        filler_list = ["um", "uh", "uhh", "umm", "like", "you know", "actually", "basically"]

    filler_segments: list[tuple[float, float]] = []
    for i, w in enumerate(words):
        w_text = w.get("word", "").strip().rstrip(".,!?").lower()
        if w_text in filler_list:
            start = w["start"]
            end = w["end"]
            if filler_segments and (start - filler_segments[-1][1]) < min_gap:
                merged_start, _ = filler_segments.pop()
                filler_segments.append((merged_start, end))
            else:
                filler_segments.append((start, end))

    if not filler_segments:
        from kb.tools.ffmpeg_adapter import _run as _cp
        _cp(["cp", input, output], check=True)
        return output

    keep_parts: list[tuple[float, float]] = []
    cursor = 0.0
    filler_dur = sum(e - s for s, e in filler_segments)

    # probe duration
    probe = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                   "-of", "csv=p=0", input], check=True)
    total_dur = float(probe.stdout.strip())

    for fs, fe in filler_segments:
        if fs - cursor > 0.05:
            keep_parts.append((cursor, fs))
        cursor = max(cursor, fe)
    if total_dur - cursor > 0.05:
        keep_parts.append((cursor, total_dur))

    if len(keep_parts) <= 1:
        from kb.tools.ffmpeg_adapter import _run as _cp
        _cp(["cp", input, output], check=True)
        return output

    filter_parts_v: list[str] = []
    filter_parts_a: list[str] = []
    for i, (ks, ke) in enumerate(keep_parts):
        filter_parts_v.append(f"[0:v]trim={ks}:{ke},setpts=PTS-STARTPTS[v{i}]")
        filter_parts_a.append(f"[0:a]atrim={ks}:{ke},asetpts=PTS-STARTPTS[a{i}]")

    v_concat = "".join(f"[v{i}]" for i in range(len(keep_parts)))
    a_concat = "".join(f"[a{i}]" for i in range(len(keep_parts)))
    filter_complex = (
        ";".join(filter_parts_v + filter_parts_a)
        + f";{v_concat}concat=n={len(keep_parts)}:v=1:a=0[vout]"
        + f";{a_concat}concat=n={len(keep_parts)}:v=0:a=1[aout]"
    )

    cmd = [
        "ffmpeg", "-i", input,
        "-filter_complex", filter_complex,
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-c:a", "aac", output,
    ]
    _run(cmd, check=True)
    return output


# ── Quality gate runner ──

def _run_quality_gates(gates: list[dict], context: dict, output_path: str) -> list[dict]:
    results: list[dict] = []
    for gate in gates:
        check = gate.get("check", "")
        try:
            if check == "edit.verify":
                from kb.tools.unified_adapter import edit
                r = edit.verify(output_path)
                results.append({"check": check, "passed": r.get("ok", False), "details": r})
            elif check == "edit.quality_full_qc":
                from kb.tools.unified_adapter import edit
                r = edit.quality_full_qc(output_path)
                passed = r.get("file_integrity", False)
                results.append({"check": check, "passed": passed, "details": r})
            elif check == "lufs_within_1db":
                target = gate.get("target", -14)
                from kb.tools.unified_adapter import edit
                r = edit.quality_audio(output_path)
                lufs = r.get("lufs", 0)
                passed = abs(lufs - target) <= 1.0
                results.append({"check": check, "passed": passed, "details": {"measured": lufs, "target": target}})
            elif check == "average_shot_length_within":
                preset = gate.get("preset", "")
                if preset in PACING_PRESETS:
                    pp = PACING_PRESETS[preset]
                    dmin, dmax = pp["cut_cadence"] if pp["cut_cadence"] else (2, 20)
                else:
                    dmin, dmax = 2, 20
                from kb.tools.unified_adapter import edit
                r = edit.probe(output_path)
                dur = r.get("duration", 0)
                passed = dmin <= dur <= dmax
                results.append({"check": check, "passed": passed, "details": {"cadence": f"{dmin}-{dmax}s", "duration": dur}})
            elif check == "duration_within":
                dmin = gate.get("min", 0)
                dmax = gate.get("max", 9999)
                from kb.tools.unified_adapter import edit
                r = edit.info(output_path)
                dur = r.get("duration", 0)
                passed = dmin <= dur <= dmax
                results.append({"check": check, "passed": passed, "details": {"duration": dur, "min": dmin, "max": dmax}})
            else:
                results.append({"check": check, "passed": False, "details": {"error": f"unknown gate: {check}"}})
        except Exception as e:
            results.append({"check": check, "passed": False, "details": {"error": str(e)}})
    return results


def _apply_post_process(strategy: str, params: dict, output_path: str) -> str:
    if strategy == "add_silent_audio":
        from kb.tools.ffmpeg_adapter import _run
        temp = output_path + ".tmp.mp4"
        _run([
            "ffmpeg", "-i", output_path,
            "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
            "-shortest", "-c:v", "copy", "-c:a", "aac", temp,
        ], check=True)
        os.replace(temp, output_path)
        return output_path
    return output_path


# ── Step executor ──

def _execute_step(step: dict, context: dict, input_path: str, output_dir: str) -> dict:
    op = step.get("operation", "unknown")
    tool = step.get("tool", "")
    params = _substitute(copy.deepcopy(step.get("params", {})), context)
    output_key = step.get("output", "")

    if op.startswith("for_each_"):
        return _execute_loop(step, context, input_path, output_dir)

    fn = tool[5:] if tool.startswith("edit.") else ""
    READ_ONLY_OPS = {"info", "transcribe", "detect_scenes", "quality_vmaf",
                     "quality_full_qc", "scope_analyze", "verify"}
    if tool.startswith("edit."):
        if "input" not in params:
            if fn in READ_ONLY_OPS:
                params["input"] = input_path
            elif context.get("_last_output"):
                params["input"] = context["_last_output"]
            else:
                params["input"] = input_path
        if "output" not in params and fn not in READ_ONLY_OPS:
            params["output"] = str(pathlib.Path(output_dir) / f"step_{context.get('_step_idx', 0):02d}_{fn}.mp4")

        from kb.tools.unified_adapter import edit
        caller = getattr(edit, fn, None)
        if caller is None:
            raise ValueError(f"unknown edit tool: {fn}")
        result = caller(**params)
        if isinstance(result, str):
            result = {"path": result}
        if isinstance(result, dict) and result.get("path") and fn not in READ_ONLY_OPS:
            context["_last_output"] = result["path"]
    elif tool.startswith("music."):
        fn = tool[6:]
        from kb.tools.unified_adapter import music
        caller = getattr(music, fn, None)
        if caller is None:
            raise ValueError(f"unknown music tool: {fn}")
        result = caller(**params)
    elif tool.startswith("recipe."):
        # Phase 5 wiring: inject context-produced inputs (transcript/chapters/scenes)
        # that earlier steps output but recipes don't always pass via $vars.
        if tool in ("recipe.find_engaging_segments", "recipe.find_key_moments",
                     "recipe.segment_by_topic"):
            if "transcript" not in params and context.get("transcript"):
                params["transcript"] = context["transcript"]
        if tool == "recipe.find_key_moments" and "scenes" not in params and context.get("scenes"):
            params["scenes"] = context["scenes"]
        if tool in ("recipe.find_action_moments", "recipe.find_best_shots"):
            if "scenes" not in params and context.get("scenes"):
                params["scenes"] = context["scenes"]
        # Pass context through so find_* functions can consume _paced_plan / _hero_moments
        result = _call_tool(tool, params, context=context)
    else:
        result = _call_tool(tool or op, params, context=context)

    step_result = {
        "operation": op,
        "tool": tool,
        "output_key": output_key,
        "result": result,
    }
    if output_key:
        context[output_key] = result
    return step_result


def _execute_loop(step: dict, context: dict, input_path: str, output_dir: str) -> dict:
    loop_var = step.get("loop_var", "item")
    source_key = step.get("source", "")
    items = context.get(source_key, context.get("segment_list", context.get("chapters", context.get("shots", []))))
    sub_steps = step.get("steps", [])
    parallel = step.get("parallel", True)
    results: list[dict] = []

    def _run_one(item: dict, idx: int) -> dict:
        ctx = {**context, loop_var: item, "_last_output": input_path, "_step_idx": 0}
        out = pathlib.Path(output_dir) / f"seg_{idx:04d}"
        out.mkdir(parents=True, exist_ok=True)
        for j, ss in enumerate(sub_steps):
            ctx["_step_idx"] = j
            _execute_step(ss, ctx, input_path, str(out))
        return ctx

    if parallel and len(items) > 1:
        with ThreadPoolExecutor(max_workers=min(len(items), 4)) as ex:
            futures = {ex.submit(_run_one, item, i): i for i, item in enumerate(items)}
            for f in as_completed(futures):
                try:
                    results.append(f.result())
                except Exception as e:
                    results.append({"error": str(e)})
    else:
        for i, item in enumerate(items):
            results.append(_run_one(item, i))

    return {"operation": op, "count": len(items), "results": results}


# ── Main runner ──

def run_recipe(
    recipe_path: str,
    input_path: str,
    *,
    output_dir: str = "",
    force_content_type: t.Optional[str] = None,
) -> dict:
    if yaml is None:
        raise ImportError("PyYAML is required. Install: pip install pyyaml")

    with open(recipe_path) as f:
        recipe = yaml.safe_load(f)

    if not output_dir:
        stem = pathlib.Path(input_path).stem
        output_dir = f"./{stem}_{recipe.get('name', 'output')}"
    out_path = pathlib.Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    context: dict = {}
    step_results: list[dict] = []

    # ── Decision logger ──
    logger = DecisionLogger() if DecisionLogger is not None else None
    if logger is not None:
        context["_logger"] = logger

    # ── Pre-run classification warning ──
    classification: t.Optional[dict] = None
    if classify_video is not None:
        try:
            classification = classify_video(input_path)
            ct = classification.get("content_type", "unknown")
            recipe_ct = recipe.get("content_type", "")
            if force_content_type:
                recipe["content_type"] = force_content_type
                print(f"Info: Forcing content_type to '{force_content_type}' (was '{recipe_ct}')")
            elif recipe_ct and ct != recipe_ct:
                print(
                    f"WARNING: Classifier detected '{ct}' but recipe expects '{recipe_ct}'",
                    file=sys.stderr,
                )
                print(f"  Reasoning: {classification.get('reasoning', '')}", file=sys.stderr)
                if recommend_recipe:
                    rec = recommend_recipe(classification)
                    if rec:
                        print(f"  Consider: using recipe '{rec}' or --force-content-type", file=sys.stderr)
            if logger is not None:
                logger.log(
                    type="classify",
                    action=f"classified as '{ct}'",
                    input=input_path,
                    output=ct,
                    reasoning=classification.get("reasoning", ""),
                )
        except Exception as e:
            print(f"Note: Classifier unavailable: {e}", file=sys.stderr)

    # ── Phase 6-9 intelligence layer (optional — degrades gracefully) ──
    # Speed: skip probe entirely if recipe doesn't reference intelligence-layer outputs
    # (most basic recipes just need trim/resize/render — probe is wasted work)
    content_type = recipe.get("content_type", "vlog")
    recipe_steps_yaml = recipe.get("steps", [])
    recipe_needs_intel = _recipe_needs_intelligence(recipe_steps_yaml)
    if _probe_video is not None and recipe_needs_intel:
        try:
            # Speed: use cache-or-probe (60x speedup on cache hit)
            if _get_or_probe is not None:
                source_profile = _get_or_probe(
                    input_path,
                    _probe_video,
                    separate_stems=recipe.get("separate_stems", False),
                    score_with_llm=False,
                    render_timeline_png=True,
                )
            else:
                source_profile = _probe_video(
                    input_path,
                    separate_stems=recipe.get("separate_stems", False),
                    score_with_llm=False,
                    render_timeline_png=True,
                )
            context["_source_profile"] = source_profile
            cache_hit = source_profile.get("_cache_hit", False)
            if logger is not None:
                logger.log(
                    type="probe",
                    action=f"multimodal probe ({'cache hit' if cache_hit else 'fresh'}): {len(source_profile.get('per_second', []))}s",
                    input=input_path,
                    output=source_profile.get("metadata", {}),
                    reasoning="Phase 6 multimodal probe (visual+audio+semantic)",
                )
        except Exception as e:
            print(f"Note: Multimodal probe unavailable: {e}", file=sys.stderr)
            context["_source_profile_error"] = str(e)

        sp = context.get("_source_profile")
        if sp and _build_relevance_map is not None:
            try:
                rm = _build_relevance_map(sp, content_type=content_type)
                context["_relevance_map"] = rm.as_dict() if hasattr(rm, "as_dict") else rm
                if logger is not None:
                    logger.log(type="relevance_map",
                               action=f"hero_moments={len(rm.hero_moments)} dead_zones={len(rm.dead_zones)}",
                               output=rm.summary, reasoning="Phase 7 edit relevance map")
            except Exception as e:
                print(f"Note: Relevance map unavailable: {e}", file=sys.stderr)

        if sp and _find_best_cuts is not None and context.get("_relevance_map"):
            try:
                cuts = _find_best_cuts(sp, context["_relevance_map"], content_type, n=20)
                context["_cut_points"] = cuts
            except Exception as e:
                print(f"Note: Cut detection unavailable: {e}", file=sys.stderr)

        if sp and context.get("_relevance_map") and _build_paced_plan is not None:
            try:
                paced = _build_paced_plan(sp, context["_relevance_map"],
                                          context.get("_cut_points", []), content_type)
                context["_paced_plan"] = paced
            except Exception as e:
                print(f"Note: Pacing engine unavailable: {e}", file=sys.stderr)

        if sp and context.get("_relevance_map") and _find_slowmo_moments is not None:
            try:
                slowmo = _find_slowmo_moments(sp, context["_relevance_map"],
                                              max_per_minute=recipe.get("max_slowmo_per_minute", 2))
                context["_slowmo_proposals"] = slowmo
            except Exception as e:
                print(f"Note: Slow-mo engine unavailable: {e}", file=sys.stderr)

        if sp and context.get("_cut_points") and _build_music_sync_plan is not None:
            try:
                music_plan = _build_music_sync_plan(sp, context["_cut_points"], context["_relevance_map"])
                context["_music_sync_plan"] = music_plan
            except Exception as e:
                print(f"Note: Music sync unavailable: {e}", file=sys.stderr)

        if sp and context.get("_relevance_map") and _detect_hero_moments is not None:
            try:
                heroes = _detect_hero_moments(sp, context["_relevance_map"])
                context["_hero_moments"] = heroes
                if logger is not None and heroes:
                    for h in heroes[:5]:
                        logger.log(type="hero_detect",
                                   action=f"level {h['level']} ({h['label']}) @ {h['start']:.1f}s",
                                   output=h["geometric_mean"],
                                   reasoning=h["fusion_reasoning"][:200],
                                   succeeded=h["level"] >= 2)
            except Exception as e:
                print(f"Note: Hero detector unavailable: {e}", file=sys.stderr)

        if not recipe.get("skip_intelligent_planning", False) and _generate_plan is not None:
            try:
                memory_hints: list[dict] = []
                if _EditPatternDB is not None:
                    db = _EditPatternDB()
                    memory_hints = db.get_memory_hints(content_type, top_n=5)
                    context["_memory_hints"] = memory_hints

                # Phase 5: Intent decomposition (VideoAgent pattern)
                intents_obj = None
                if _parse_intents is not None:
                    try:
                        intents_obj = _parse_intents(
                            recipe.get("description", ""), content_type, sp
                        )
                        context["_intents"] = intents_obj
                        if logger is not None:
                            logger.log(type="intent_parse",
                                       action=f"explicit={len(intents_obj['explicit'])} implicit={len(intents_obj['implicit'])}",
                                       output=intents_obj["all"],
                                       reasoning="Phase 5 VideoAgent intent decomposition")
                    except Exception:
                        intents_obj = None
                all_intents = (intents_obj or {}).get("all", recipe.get("intents", []))

                # Phase 5: Editing Research pure-reasoning sub-phase (Crayotter pattern)
                editing_blueprint = None
                if _research_edit is not None:
                    try:
                        router = _get_router() if _get_router is not None else None
                        editing_blueprint = _research_edit(
                            sp, context.get("_relevance_map", {}),
                            content_type, all_intents, router,
                        )
                        context["_editing_blueprint"] = editing_blueprint
                        if logger is not None:
                            logger.log(type="editing_research",
                                       action=f"blueprint source={editing_blueprint.get('source')}",
                                       output=editing_blueprint.get("narrative_strategy", "")[:100],
                                       reasoning="Phase 5 Crayotter Editing Research sub-phase (no tools)")
                    except Exception as e:
                        print(f"Note: Editing research unavailable: {e}", file=sys.stderr)

                edit_plan = _generate_plan(
                    sp, context.get("_relevance_map", {}), context.get("_cut_points", []),
                    context.get("_paced_plan", {}), context.get("_slowmo_proposals", []),
                    context.get("_music_sync_plan", {}), content_type,
                    all_intents, memory_hints,
                    plan_llm_model=recipe.get("plan_llm", "ollama/qwen2.5-coder:7b"),
                    max_critique_rounds=3,
                    editing_blueprint=editing_blueprint,
                )
                context["_edit_plan"] = edit_plan

                # Phase 5: Build orchestrator (Project Montage per-modality sub-agents)
                if _orchest_build is not None:
                    try:
                        orchestration = _orchest_build(edit_plan)
                        context["_build_orchestration"] = orchestration
                        if logger is not None:
                            logger.log(type="build_orchestrate",
                                       action=f"sub_agents={list(orchestration.get('sub_agents', {}).keys())}",
                                       output=orchestration.get("parallel_groups", []),
                                       reasoning="Phase 5 Project Montage per-modality sub-agents")
                    except Exception:
                        pass

                if logger is not None:
                    critic = edit_plan.get("plan_critic_result", {}) or {}
                    logger.log(type="plan_critic",
                               action=f"approved={critic.get('approved')} rounds={critic.get('rounds')}",
                               output=critic.get("approved"),
                               reasoning=critic.get("reasoning", ""),
                               succeeded=critic.get("approved", False))
            except Exception as e:
                print(f"Note: Intelligent planner unavailable: {e}", file=sys.stderr)

        # Phase 5: Artifact-grounded traceability (Crayotter pattern)
        # Save per-phase artifacts to the output dir for replayability/audit
        if _ArtifactStore is not None:
            try:
                store = _ArtifactStore(str(out_path))
                if context.get("_source_profile"):
                    store.save_json("source_profile", context["_source_profile"])
                if context.get("_relevance_map"):
                    store.save_json("relevance_map", context["_relevance_map"])
                if context.get("_cut_points"):
                    store.save_json("cut_points", context["_cut_points"])
                if context.get("_paced_plan"):
                    store.save_json("paced_plan", context["_paced_plan"])
                if context.get("_slowmo_proposals"):
                    store.save_json("slowmo_proposals", context["_slowmo_proposals"])
                if context.get("_music_sync_plan"):
                    store.save_json("music_sync_plan", context["_music_sync_plan"])
                if context.get("_hero_moments"):
                    store.save_json("hero_moments", context["_hero_moments"])
                if context.get("_editing_blueprint"):
                    bp = context["_editing_blueprint"]
                    store.save_json("editing_blueprint", {k: v for k, v in bp.items() if k != "blueprint_md"})
                    if bp.get("blueprint_md"):
                        store.save_markdown("editing_blueprint", bp["blueprint_md"])
                if context.get("_edit_plan"):
                    store.save_json("edit_plan", context["_edit_plan"])
                    if context["_edit_plan"].get("storyboard"):
                        store.save_markdown("storyboard", context["_edit_plan"]["storyboard"])
                context["_artifact_store"] = store
            except Exception as e:
                print(f"Note: Artifact store unavailable: {e}", file=sys.stderr)

    # ── Step execution ──
    for i, step in enumerate(recipe.get("steps", [])):
        context["_step_idx"] = i
        step_result = _execute_step(step, context, input_path, str(out_path))
        step["_index"] = i
        step_result["step_index"] = i
        step_results.append(step_result)
        if logger is not None:
            logger.log(
                type="recipe_step",
                action=f"executed {step_result.get('operation', step_result.get('tool', 'unknown'))}",
                output=step_result.get("output_key", ""),
                reasoning=f"step index {i}",
            )

    # ── VLM highlight verification ──
    if recipe.get("verify_moments") and context.get("moments_list"):
        try:
            from kb.tools.vlm_adapter import verify_highlights
            vlm_results = verify_highlights(input_path, context["moments_list"])
            context["_vlm_verification"] = vlm_results
            if logger is not None:
                for v in vlm_results:
                    m = v.get("moment", {})
                    logger.log(
                        type="vlm_verify",
                        action=f"verify '{m.get('category')}' @ {m.get('start', 0):.1f}s",
                        output=v.get("verified"),
                        reasoning=v.get("reasoning", ""),
                        succeeded=v.get("verified") is not False,
                    )
        except Exception as e:
            context["_vlm_verification_error"] = str(e)

    final_output = context.get("_last_output", "")
    if not final_output:
        quality_results = [{
            "check": "edit.verify",
            "passed": False,
            "details": {"error": "no _last_output in context — recipe produced no renderable output"}
        }]
    else:
        canonical = str(out_path / "output.mp4")
        if final_output != canonical and os.path.exists(final_output):
            try:
                if os.path.exists(canonical):
                    os.remove(canonical)
                os.link(final_output, canonical)
            except OSError:
                import shutil
                shutil.copy2(final_output, canonical)
            final_output = canonical

        gates = recipe.get("quality_gates", [])
        quality_results = _run_quality_gates(gates, context, final_output) if gates else []

    # ── Log quality gates ──
    if logger is not None:
        for g in quality_results:
            logger.log(
                type="gate_pass" if g.get("passed") else "gate_fail",
                action=g.get("check", "unknown"),
                output=g.get("passed"),
                reasoning=str(g.get("details", "")),
                succeeded=g.get("passed", False),
            )

    # ── Auto-recovery loop ──
    recovery_engine = RecoveryEngine() if RecoveryEngine is not None else None
    max_rounds = 3
    recovery_attempts: list[dict] = []
    round_num = 0

    while (
        recovery_engine is not None
        and not all(g.get("passed", False) for g in quality_results)
        and round_num < max_rounds
    ):
        round_num += 1
        any_recovered = False
        for gi, gate in enumerate(quality_results):
            if gate.get("passed", False):
                continue
            plan = recovery_engine.can_recover(gate, context)
            if plan is None:
                continue
            any_recovered = True
            strategy = plan["strategy"]
            step_idx = plan["step_index"]
            overrides = plan["param_overrides"]

            if step_idx >= 0:
                step_copy = copy.deepcopy(recipe["steps"][step_idx])
                step_copy.setdefault("params", {}).update(overrides)
                step_result = _execute_step(step_copy, context, input_path, str(out_path))
                step_result["step_index"] = step_idx
                step_results.append(step_result)
            elif strategy == "add_silent_audio":
                final_output = _apply_post_process(strategy, overrides, final_output)

            result_rr = RecoveryResult(
                attempted=True,
                strategy_name=strategy,
                step_index=step_idx,
                param_overrides=overrides,
                retry_count=recovery_engine.retry_counts.get(step_idx, 0),
                succeeded=False,
                detail=f"round {round_num}",
            )
            recovery_engine.record_attempt(result_rr)
            if logger is not None:
                logger.log(
                    type="recover",
                    action=f"strategy '{strategy}' on step {step_idx}",
                    input=overrides,
                    output=False,
                    reasoning=f"round {round_num}",
                    succeeded=False,
                )

        if not any_recovered:
            break

        if final_output and os.path.exists(final_output):
            quality_results = _run_quality_gates(gates, context, final_output)
        else:
            break

    if recovery_engine is not None:
        recovery_attempts = recovery_engine.summary()

    # ── Failed VLM warnings ──
    vlm_verification = context.get("_vlm_verification")
    if vlm_verification:
        failed = [v for v in vlm_verification
                  if v.get("verified") is False and v.get("confidence", 0) > 0.7]
        if failed:
            print(f"\n[VLM] {len(failed)} moment(s) failed visual verification:", file=sys.stderr)
            for fv in failed:
                m = fv["moment"]
                print(f"  - {m.get('category')} @ {m.get('start'):.1f}s: {fv['reasoning']}", file=sys.stderr)
            print("  Consider manual review or re-running with different categories.\n", file=sys.stderr)

    # ── Phase 9 M4: 7-dimension reviewer (on the final output) ──
    review_result: t.Optional[dict] = None
    if _review_output is not None and final_output and os.path.exists(final_output):
        try:
            sp = context.get("_source_profile", {})
            review_result = _review_output(
                final_output,
                context.get("_edit_plan", {"assumptions": {}, "steps": []}),
                sp,
                context.get("_paced_plan", {"summary": {}}),
                content_type,
            )
            if logger is not None:
                logger.log(type="review",
                           action=f"overall={review_result.get('overall')} passed={review_result.get('passed')}",
                           output=review_result.get("overall"),
                           reasoning=review_result.get("reasoning", ""),
                           succeeded=review_result.get("passed", False))
        except Exception as e:
            print(f"Note: Reviewer unavailable: {e}", file=sys.stderr)

    # ── Phase 9 M5: edit-pattern memory write ──
    memory_writes: list[dict] = []
    if _EditPatternDB is not None:
        try:
            db = _EditPatternDB()
            run_id = context.get("_run_id", f"{recipe.get('name', 'unknown')}_{int(time.time())}")
            review_overall = (review_result or {}).get("overall") if review_result else None
            review_vmaf = (review_result or {}).get("vmaf") if review_result else None
            review_passed = (review_result or {}).get("passed", False) if review_result else False
            for step in recipe.get("steps", []):
                tool = step.get("tool", "")
                if tool.startswith("edit."):
                    technique = tool[5:]
                    params = step.get("params", {})
                    db.record_outcome(content_type, technique, params,
                                      success=review_passed, vmaf=review_vmaf,
                                      reviewer_score=review_overall, run_id=run_id)
                    memory_writes.append({"technique": technique, "success": review_passed})
        except Exception as e:
            print(f"Note: Memory write unavailable: {e}", file=sys.stderr)

    # ── Phase 5: AVE retry_if gate evaluation ──
    retry_gates_triggered: list[dict] = []
    if _parse_retry_if is not None and recovery_engine is not None:
        try:
            retry_gates = _parse_retry_if(recipe)
            if retry_gates:
                retry_gates_triggered = recovery_engine.evaluate_retry_gates(
                    retry_gates, review_result=review_result, quality_results=quality_results
                )
                if retry_gates_triggered and logger is not None:
                    for g in retry_gates_triggered:
                        logger.log(type="retry_gate",
                                   action=f"metric={g['metric']} value={g.get('actual_value', 0):.3f} < {g['threshold']}",
                                   output=g.get("actual_value"),
                                   reasoning=f"feedback_target={g.get('feedback_target', 'editor')}",
                                   succeeded=False)
        except Exception as e:
            print(f"Note: Retry gate evaluation unavailable: {e}", file=sys.stderr)

    # ── Phase 5: save review artifact + artifact store summary ──
    if context.get("_artifact_store") and review_result:
        try:
            context["_artifact_store"].save_json("review", review_result)
        except Exception:
            pass

    # ── Finalize manifest ──
    manifest = {
        "recipe": recipe.get("name", "unknown"),
        "version": recipe.get("version", "1.0"),
        "input": input_path,
        "output_dir": str(out_path.resolve()),
        "steps_executed": len(step_results),
        "gates_passed": all(g.get("passed", False) for g in quality_results),
        "quality_gates": quality_results,
        "step_results": step_results,
        "classification": classification,
        # Phase 6-9 intelligence layer
        "source_profile_metadata": (context.get("_source_profile") or {}).get("metadata", {}),
        "source_profile_components": (context.get("_source_profile") or {}).get("components_used", {}),
        "relevance_map_summary": (context.get("_relevance_map") or {}).get("summary", {}),
        "hero_moments": context.get("_hero_moments", []),
        "cut_points": (context.get("_cut_points") or [])[:10],
        "paced_plan_summary": (context.get("_paced_plan") or {}).get("summary", {}),
        "slowmo_proposals": context.get("_slowmo_proposals", []),
        "music_sync_plan": context.get("_music_sync_plan", {}),
        "edit_plan": context.get("_edit_plan"),
        "memory_hints": context.get("_memory_hints", []),
        "review_result": review_result,
        "memory_writes": memory_writes,
        # Phase 5 additions
        "intents": context.get("_intents"),
        "editing_blueprint": (context.get("_editing_blueprint") or {}).get("source") if context.get("_editing_blueprint") else None,
        "build_orchestration": context.get("_build_orchestration"),
        "retry_gates_triggered": retry_gates_triggered,
        "artifacts": (context.get("_artifact_store") or None).summary() if context.get("_artifact_store") else None,
        # Existing Phase 4 fields
        "vlm_verification": vlm_verification,
        "recovery_attempts": recovery_attempts,
        "decision_log": logger.as_list() if logger is not None else [],
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    manifest_path = out_path / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, default=str)

    return manifest


def cli() -> None:
    parser = argparse.ArgumentParser(description="Run a recipe pack on input video")
    parser.add_argument("recipe", nargs="?", help="Path to recipe YAML file (required unless --list or --recommend)")
    parser.add_argument("input", nargs="?", help="Path to input video file (required unless --list)")
    parser.add_argument("--output", "-o", default="", help="Output directory")
    parser.add_argument("--list", action="store_true", help="List available recipes")
    parser.add_argument("--recommend", action="store_true", help="Classify input and recommend a recipe, then exit")
    parser.add_argument("--force-content-type", help="Override recipe content_type before execution")
    parser.add_argument("--explain", action="store_true",
                        help="After running, print the decision log in human-readable form")
    parser.add_argument("--probe-only", action="store_true",
                        help="Run multimodal probe and save SourceProfile JSON, then exit")
    parser.add_argument("--analyze-only", action="store_true",
                        help="Run probe + relevance map + cut detection + pacing + slow-mo + music sync + hero detection, save JSON, exit")
    parser.add_argument("--no-intelligent-planning", action="store_true",
                        help="Skip LLM plan generation + critique; use recipe YAML directly")
    args = parser.parse_args()

    if args.list:
        if yaml is None:
            print("ERROR: PyYAML is required. Install: pip install pyyaml", file=sys.stderr)
            sys.exit(1)
        recipes_dir = pathlib.Path(__file__).resolve().parent.parent.parent / "recipes"
        if not recipes_dir.exists():
            print(f"ERROR: recipes directory not found at {recipes_dir}", file=sys.stderr)
            sys.exit(1)
        print(f"Available recipes in {recipes_dir}:")
        print()
        for f in sorted(recipes_dir.glob("*.yaml")):
            try:
                with open(f) as fh:
                    r = yaml.safe_load(fh) or {}
                name = r.get("name", f.stem)
                desc = r.get("description", "")
                ct = r.get("content_type", "?")
                print(f"  {f.name:<35s} [{ct:<12s}] {desc}")
            except yaml.YAMLError as e:
                print(f"  {f.name:<35s} [PARSE ERROR] {e}")
        return

    if args.recommend:
        if not args.input:
            parser.error("--recommend requires an input file")
        if classify_video is None:
            print("ERROR: classifier module not available (pip install -e .)", file=sys.stderr)
            sys.exit(1)
        result = classify_video(args.input)
        rec = recommend_recipe(result) if recommend_recipe else None
        output = {
            "content_type": result["content_type"],
            "confidence": result["confidence"],
            "recommended_recipe": rec,
            "reasoning": result["reasoning"],
            "signals": {k: v for k, v in result.get("signals", {}).items() if isinstance(v, (int, float))},
        }
        print(json.dumps(output, indent=2, default=str))
        sys.exit(0)

    if args.probe_only:
        input_file = args.input or args.recipe
        if not input_file:
            parser.error("--probe-only requires an input file")
        if _probe_video is None:
            print("ERROR: probe module not available (pip install -e .)", file=sys.stderr)
            sys.exit(1)
        from kb.tools.probe import save_profile
        # Speed: use cache-or-probe (60x speedup on cache hit)
        if _get_or_probe is not None:
            profile = _get_or_probe(input_file, _probe_video, separate_stems=False, score_with_llm=False)
        else:
            profile = _probe_video(input_file, separate_stems=False, score_with_llm=False)
        out_dir = pathlib.Path(args.output or ".")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_json = out_dir / f"{pathlib.Path(input_file).stem}_profile.json"
        save_profile(profile, str(out_json))
        comps = profile.get("components_used", {})
        print(f"SourceProfile saved to {out_json}")
        print(f"  duration: {profile.get('metadata', {}).get('duration', 0):.1f}s")
        print(f"  visual components: {comps.get('visual', [])}")
        print(f"  audio components:  {comps.get('audio', [])}")
        print(f"  semantic components: {comps.get('semantic', [])}")
        sys.exit(0)

    if args.analyze_only:
        input_file = args.input or args.recipe
        if not input_file:
            parser.error("--analyze-only requires an input file")
        if _probe_video is None:
            print("ERROR: probe module not available (pip install -e .)", file=sys.stderr)
            sys.exit(1)
        content_type_an = "vlog"
        recipe_path_an = args.recipe if (args.recipe and args.input) else None
        if recipe_path_an and yaml is not None:
            try:
                with open(recipe_path_an) as f:
                    r = yaml.safe_load(f) or {}
                content_type_an = r.get("content_type", "vlog")
            except Exception:
                pass
        # Speed: use cache-or-probe (60x speedup on cache hit)
        if _get_or_probe is not None:
            profile = _get_or_probe(input_file, _probe_video, separate_stems=False, score_with_llm=False)
        else:
            profile = _probe_video(input_file, separate_stems=False, score_with_llm=False)
        rm = _build_relevance_map(profile, content_type=content_type_an) if _build_relevance_map else None
        rm_dict = rm.as_dict() if rm and hasattr(rm, "as_dict") else (rm or {})
        cuts = _find_best_cuts(profile, rm_dict, content_type_an, n=20) if _find_best_cuts and rm else []
        paced = _build_paced_plan(profile, rm_dict, cuts, content_type_an) if _build_paced_plan and rm else {}
        slowmo = _find_slowmo_moments(profile, rm_dict, max_per_minute=2) if _find_slowmo_moments and rm else []
        music = _build_music_sync_plan(profile, cuts, rm_dict) if _build_music_sync_plan and rm else {}
        heroes = _detect_hero_moments(profile, rm_dict) if _detect_hero_moments and rm else []
        analysis = {
            "source_profile": profile, "relevance_map": rm_dict,
            "cut_points": cuts, "paced_plan": paced,
            "slowmo_proposals": slowmo, "music_sync_plan": music,
            "hero_moments": heroes,
        }
        out_dir = pathlib.Path(args.output or ".")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_json = out_dir / f"{pathlib.Path(input_file).stem}_analysis.json"
        with open(out_json, "w") as f:
            json.dump(analysis, f, indent=2, default=str)
        print(f"Analysis saved to {out_json}")
        print(f"  hero moments: {len(heroes)}")
        print(f"  dead zones:   {len(rm_dict.get('dead_zones', []))}")
        print(f"  cut points:   {len(cuts)}")
        print(f"  slow-mo props:{len(slowmo)}")
        sys.exit(0)

    if not args.recipe or not args.input:
        parser.error("recipe and input are required unless --list or --recommend or --probe-only or --analyze-only is used")

    manifest = run_recipe(args.recipe, args.input, output_dir=args.output, force_content_type=args.force_content_type)
    print(json.dumps(manifest, indent=2, default=str))

    if args.explain:
        log = manifest.get("decision_log", [])
        print("\n=== DECISION LOG ===")
        for d in log:
            icon = "[OK]" if d.get("succeeded", True) else "[!]"
            print(f"  {d['timestamp']} {icon} {d['type']:<18s} {d['action']}")
            if d.get("reasoning"):
                print(f"        reasoning: {d['reasoning'][:120]}")
        print(f"\nTotal decisions: {len(log)}")


if __name__ == "__main__":
    cli()
