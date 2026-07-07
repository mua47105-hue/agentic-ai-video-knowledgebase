"""
Intelligent Cut-Point Detection (Phase 7) — Walter Murch's Rule of Six as code.

Given a SourceProfile + RelevanceMap, finds candidate cut points and scores each
on Murch's 6 dimensions (emotion 0.51, story 0.23, rhythm 0.10, eye_trace 0.07,
plane_2d 0.05, space_3d 0.04). Composite ≥ 0.6 = acceptable cut.

Also enforces 4 boundary constraints:
  - Syntactic: prefer sentence-end (from transcript)
  - Breath:    prefer silence boundaries (Silero VAD)
  - Beat:      snap to downbeats when music present
  - Shot:      prefer scene boundaries (PySceneDetect)

Public surface:
  - find_cut_points(source_profile, relevance_map, content_type, **opts) -> list[dict]
  - find_best_cuts(source_profile, relevance_map, content_type, n) -> list[dict]
"""
from __future__ import annotations

import typing as t


MURCH_WEIGHTS = {
    "emotion": 0.51,
    "story": 0.23,
    "rhythm": 0.10,
    "eye_trace": 0.07,
    "plane_2d": 0.05,
    "space_3d": 0.04,
}


def find_cut_points(source_profile: dict, relevance_map: dict,
                    content_type: str = "vlog",
                    target_density: str = "medium",
                    min_score: float = 0.6) -> list[dict]:
    """Find candidate cut points and score each on Murch's 6 dimensions."""
    candidates: set[float] = set()

    # Shot boundaries
    for ts in source_profile.get("visual", {}).get("scene_boundaries", []):
        candidates.add(round(float(ts), 2))

    # Silence boundaries
    for seg in source_profile.get("audio", {}).get("silence_segments", []):
        candidates.add(round(float(seg["start"]), 2))
        candidates.add(round(float(seg["end"]), 2))

    # Sentence boundaries
    for seg in source_profile.get("semantic", {}).get("transcript", []):
        text = seg.get("text", "")
        if text.rstrip().endswith((".", "!", "?")):
            candidates.add(round(float(seg.get("end", 0)), 2))

    # Beat boundaries (downbeats preferred)
    for beat in source_profile.get("audio", {}).get("downbeats", []):
        candidates.add(round(float(beat), 2))

    per_second = source_profile.get("per_second", [])
    ps_by_ts = {ps["ts"]: ps for ps in per_second}
    rm_by_ts = {ps["ts"]: ps for ps in relevance_map.get("per_second", [])}

    MIN_GAP = {"sparse": 15.0, "medium": 7.0, "dense": 3.0}.get(target_density, 7.0)
    duration = source_profile.get("metadata", {}).get("duration", 0)
    sorted_candidates = sorted(candidates)
    last_cut_ts = -100.0
    cut_points: list[dict] = []

    for ts in sorted_candidates:
        if ts < 0.5 or ts > duration - 0.5:
            continue
        if ts - last_cut_ts < MIN_GAP:
            continue
        sec = int(ts)
        ps = ps_by_ts.get(sec, {})
        rm = rm_by_ts.get(sec, {})

        emotion = _score_emotion(ps, rm)
        story = _score_story(ps, rm)
        rhythm = _score_rhythm(ts, content_type, last_cut_ts, MIN_GAP)
        eye_trace = _score_eye_trace(ps, ps_by_ts.get(sec - 1, {}))
        plane_2d = _score_plane_2d(ps)
        space_3d = _score_space_3d(ps, ps_by_ts.get(sec - 1, {}))

        composite = (
            MURCH_WEIGHTS["emotion"] * emotion +
            MURCH_WEIGHTS["story"] * story +
            MURCH_WEIGHTS["rhythm"] * rhythm +
            MURCH_WEIGHTS["eye_trace"] * eye_trace +
            MURCH_WEIGHTS["plane_2d"] * plane_2d +
            MURCH_WEIGHTS["space_3d"] * space_3d
        )
        if composite < min_score:
            continue

        reasons = _identify_boundary_reasons(ts, source_profile)
        reasoning_parts = []
        if emotion >= 0.7:
            reasoning_parts.append(f"strong emotional continuity ({emotion:.2f})")
        if story >= 0.7:
            reasoning_parts.append(f"advances narrative ({story:.2f})")
        if rhythm >= 0.7:
            reasoning_parts.append(f"good rhythm ({rhythm:.2f})")
        if reasons:
            reasoning_parts.append(f"boundary: {', '.join(reasons)}")

        cut_points.append({
            "timestamp": ts,
            "composite_score": composite,
            "emotion": emotion,
            "story": story,
            "rhythm": rhythm,
            "eye_trace": eye_trace,
            "plane_2d": plane_2d,
            "space_3d": space_3d,
            "boundary_reasons": reasons,
            "reasoning": "; ".join(reasoning_parts) if reasoning_parts else f"composite {composite:.2f}",
        })
        last_cut_ts = ts

    cut_points.sort(key=lambda cp: -cp["composite_score"])
    return cut_points


def find_best_cuts(source_profile: dict, relevance_map: dict,
                   content_type: str, n: int = 10) -> list[dict]:
    all_cuts = find_cut_points(source_profile, relevance_map, content_type,
                                target_density="medium", min_score=0.6)
    return all_cuts[:n]


def _score_emotion(ps: dict, rm: dict) -> float:
    arousal = float(ps.get("face_arousal", 0.0))
    emotional_intensity = float(rm.get("emotional_intensity", 0.0))
    if emotional_intensity > 0.6:
        return 0.4
    elif arousal < 0.3:
        return 0.9
    return 0.6


def _score_story(ps: dict, rm: dict) -> float:
    semantic_importance = float(rm.get("semantic_importance", 0.5))
    text = ps.get("text", "")
    if text.rstrip().endswith((".", "!", "?")):
        return min(1.0, 0.5 + semantic_importance * 0.5)
    elif text and not text.endswith((" ", "\n")):
        return 0.3
    return 0.6


def _score_rhythm(ts: float, content_type: str,
                  last_cut_ts: float, min_gap: float) -> float:
    PACING_TARGET = {
        "vlog": 7.0, "social-short": 4.0, "tutorial": 30.0, "podcast": 60.0,
        "cinematic": 12.0, "interview": 20.0, "documentary": 15.0,
        "talking-head": 15.0, "music-video": 4.0, "event": 10.0,
    }
    target = PACING_TARGET.get(content_type, 10.0)
    gap = ts - last_cut_ts
    if gap < min_gap:
        return 0.2
    elif gap == target:
        return 1.0
    elif gap < target * 1.5:
        return 0.8
    elif gap < target * 2.5:
        return 0.6
    return 0.4


def _score_eye_trace(ps: dict, prev_ps: dict) -> float:
    scale = ps.get("shot_scale", "unknown")
    prev_scale = prev_ps.get("shot_scale", "unknown")
    face = ps.get("face_present", False)
    prev_face = prev_ps.get("face_present", False)
    if face and prev_face:
        return 0.9
    elif scale == prev_scale and scale != "unknown":
        return 0.7
    elif scale == "unknown" or prev_scale == "unknown":
        return 0.5
    return 0.3


def _score_plane_2d(ps: dict) -> float:
    aesthetic = float(ps.get("aesthetic_score", 0.5))
    ocr = ps.get("ocr_text")
    if ocr:
        return 0.8
    return aesthetic


def _score_space_3d(ps: dict, prev_ps: dict) -> float:
    scale = ps.get("shot_scale", "unknown")
    prev_scale = prev_ps.get("shot_scale", "unknown")
    if scale != prev_scale and scale != "unknown" and prev_scale != "unknown":
        return 0.8
    elif scale == prev_scale and scale != "unknown":
        return 0.4
    return 0.5


def _identify_boundary_reasons(ts: float, source_profile: dict) -> list[str]:
    reasons: list[str] = []
    tolerance = 0.5
    for sb in source_profile.get("visual", {}).get("scene_boundaries", []):
        if abs(float(sb) - ts) < tolerance:
            reasons.append("shot_boundary")
            break
    for seg in source_profile.get("audio", {}).get("silence_segments", []):
        if abs(float(seg["start"]) - ts) < tolerance or abs(float(seg["end"]) - ts) < tolerance:
            reasons.append("silence")
            break
    for seg in source_profile.get("semantic", {}).get("transcript", []):
        if abs(float(seg.get("end", 0)) - ts) < tolerance:
            text = seg.get("text", "")
            if text.rstrip().endswith((".", "!", "?")):
                reasons.append("sentence_end")
                break
    for beat in source_profile.get("audio", {}).get("downbeats", []):
        if abs(float(beat) - ts) < tolerance:
            reasons.append("beat")
            break
    return reasons
