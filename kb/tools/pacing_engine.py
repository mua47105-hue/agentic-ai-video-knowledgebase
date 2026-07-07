"""
Pacing Engine (Phase 8) — content-type pacing profiles + pattern-interrupt enforcement.

Takes a relevance map + cut points + content type, produces a paced cut plan that
respects:
  - Pattern-interrupt interval (per content type, from empirical RESEARCH-2 data)
  - Hook window (first 1.5-3s must have verbal+visual interrupt)
  - Shot-length distribution (target mean + variance per content type)
  - Hero moment preservation (never cut inside a hero moment)
  - Dead zone elimination (always cut around dead zones)

Public surface:
  - build_paced_plan(source_profile, relevance_map, cut_points, content_type) -> dict
  - PACING_PROFILES (10 content types)
"""
from __future__ import annotations

import statistics
import typing as t


PACING_PROFILES: dict[str, dict] = {
    "vlog": {
        "pattern_interrupt_min": 5.0, "pattern_interrupt_max": 10.0,
        "shot_length_mean": 7.0, "shot_length_std": 3.0,
        "hook_window": 1.5, "hook_requires": ["verbal", "visual"],
        "dead_zone_max": 4.0, "hero_protection": True,
    },
    "social-short": {
        "pattern_interrupt_min": 3.0, "pattern_interrupt_max": 5.0,
        "shot_length_mean": 4.0, "shot_length_std": 1.5,
        "hook_window": 1.5, "hook_requires": ["verbal", "visual"],
        "dead_zone_max": 2.0, "hero_protection": True,
    },
    "podcast": {
        "pattern_interrupt_min": 30.0, "pattern_interrupt_max": 90.0,
        "shot_length_mean": 60.0, "shot_length_std": 30.0,
        "hook_window": 3.0, "hook_requires": ["verbal"],
        "dead_zone_max": 8.0, "hero_protection": True,
    },
    "tutorial": {
        "pattern_interrupt_min": 30.0, "pattern_interrupt_max": 75.0,
        "shot_length_mean": 45.0, "shot_length_std": 20.0,
        "hook_window": 3.0, "hook_requires": ["verbal"],
        "dead_zone_max": 6.0, "hero_protection": True,
    },
    "cinematic": {
        "pattern_interrupt_min": 8.0, "pattern_interrupt_max": 15.0,
        "shot_length_mean": 12.0, "shot_length_std": 5.0,
        "hook_window": 3.0, "hook_requires": ["visual"],
        "dead_zone_max": 5.0, "hero_protection": True,
    },
    "documentary": {
        "pattern_interrupt_min": 8.0, "pattern_interrupt_max": 15.0,
        "shot_length_mean": 10.0, "shot_length_std": 4.0,
        "hook_window": 3.0, "hook_requires": ["verbal"],
        "dead_zone_max": 5.0, "hero_protection": True,
    },
    "interview": {
        "pattern_interrupt_min": 15.0, "pattern_interrupt_max": 30.0,
        "shot_length_mean": 20.0, "shot_length_std": 8.0,
        "hook_window": 3.0, "hook_requires": ["verbal"],
        "dead_zone_max": 5.0, "hero_protection": True,
    },
    "talking-head": {
        "pattern_interrupt_min": 10.0, "pattern_interrupt_max": 20.0,
        "shot_length_mean": 15.0, "shot_length_std": 5.0,
        "hook_window": 3.0, "hook_requires": ["verbal"],
        "dead_zone_max": 5.0, "hero_protection": True,
    },
    "music-video": {
        "pattern_interrupt_min": 3.0, "pattern_interrupt_max": 8.0,
        "shot_length_mean": 4.0, "shot_length_std": 2.0,
        "hook_window": 1.5, "hook_requires": ["visual", "audio"],
        "dead_zone_max": 2.0, "hero_protection": True,
    },
    "event": {
        "pattern_interrupt_min": 5.0, "pattern_interrupt_max": 12.0,
        "shot_length_mean": 8.0, "shot_length_std": 4.0,
        "hook_window": 3.0, "hook_requires": ["visual"],
        "dead_zone_max": 4.0, "hero_protection": True,
    },
}


def build_paced_plan(source_profile: dict, relevance_map: dict,
                     cut_points: list[dict], content_type: str) -> dict:
    """Build a paced cut plan from relevance map + cut points + content type."""
    profile = PACING_PROFILES.get(content_type, PACING_PROFILES["vlog"])
    duration = source_profile.get("metadata", {}).get("duration", 0)
    hero_moments = relevance_map.get("hero_moments", [])
    dead_zones = relevance_map.get("dead_zones", [])

    sorted_cuts = sorted(cut_points, key=lambda c: c.get("timestamp", 0))
    boundaries = [0.0] + [c["timestamp"] for c in sorted_cuts] + [duration]
    boundaries = sorted(set(boundaries))

    segments: list[dict] = []
    for i in range(len(boundaries) - 1):
        seg_start = boundaries[i]
        seg_end = boundaries[i + 1]
        seg_duration = seg_end - seg_start
        if seg_duration < 0.5:
            continue
        keep, reason, score = _decide_segment(
            seg_start, seg_end, seg_duration, hero_moments, dead_zones, profile
        )
        segments.append({
            "start": seg_start, "end": seg_end, "keep": keep,
            "reason": reason, "pacing_score": score,
        })

    hook_satisfied, hook_reason = _check_hook_window(
        segments[:3], source_profile.get("per_second", []),
        profile["hook_requires"], profile["hook_window"]
    )
    violations = _find_pacing_violations(segments, profile)

    kept = [s for s in segments if s["keep"]]
    cut = [s for s in segments if not s["keep"]]
    total_kept = sum(s["end"] - s["start"] for s in kept)
    total_cut = sum(s["end"] - s["start"] for s in cut)

    summary = {
        "content_type": content_type,
        "total_segments": len(segments),
        "kept_segments": len(kept),
        "cut_segments": len(cut),
        "total_kept_duration": round(total_kept, 2),
        "total_cut_duration": round(total_cut, 2),
        "compression_ratio": round(total_kept / duration, 3) if duration > 0 else 0,
        "avg_shot_length": round(statistics.mean([s["end"] - s["start"] for s in kept]), 2) if kept else 0,
        "hook_window_satisfied": hook_satisfied,
        "pacing_violation_count": len(violations),
    }
    return {
        "segments": segments,
        "total_kept_duration": total_kept,
        "total_cut_duration": total_cut,
        "hook_window_satisfied": hook_satisfied,
        "hook_window_reason": hook_reason,
        "pacing_violations": violations,
        "summary": summary,
    }


def _decide_segment(start: float, end: float, duration: float,
                    hero_moments: list[dict], dead_zones: list[dict],
                    profile: dict) -> tuple[bool, str, float]:
    # Hero protection
    if profile.get("hero_protection", True):
        for hm in hero_moments:
            if start < hm["end"] and end > hm["start"]:
                overlap = min(end, hm["end"]) - max(start, hm["start"])
                if overlap > 0.5:
                    return True, f"hero_moment_overlap (peak {hm['peak_score']:.2f})", 1.0
    # Dead zone elimination
    for dz in dead_zones:
        if start >= dz["start"] and end <= dz["end"]:
            return False, f"dead_zone (avg scores {dz.get('avg_scores', {})})", 0.0
    # Pacing profile adherence
    shot_mean = profile["shot_length_mean"]
    shot_std = profile["shot_length_std"]
    if duration > shot_mean + 2 * shot_std:
        return True, f"long_segment ({duration:.1f}s vs target {shot_mean}s)", 0.4
    if abs(duration - shot_mean) <= shot_std:
        return True, f"on_target ({duration:.1f}s ≈ {shot_mean}s)", 0.9
    if duration < profile["pattern_interrupt_min"]:
        return True, f"short_segment ({duration:.1f}s < min {profile['pattern_interrupt_min']}s)", 0.6
    return True, f"within_profile ({duration:.1f}s)", 0.7


def _check_hook_window(segments: list[dict], per_second: list[dict],
                       hook_requires: list[str], hook_window: float) -> tuple[bool, str]:
    if not segments:
        return False, "no segments in hook window"
    first_seg = segments[0]
    if first_seg["end"] - first_seg["start"] > hook_window * 2:
        return False, f"first segment too long ({first_seg['end'] - first_seg['start']:.1f}s > {hook_window * 2}s)"
    first_window = [ps for ps in per_second if float(ps.get("ts", 0)) < hook_window]
    has_verbal = any(ps.get("audio_speech") or ps.get("text") for ps in first_window)
    has_visual = any(float(ps.get("motion_energy", 0)) > 0.3 or ps.get("face_present") for ps in first_window)
    has_audio = any(ps.get("audio_onset") or ps.get("audio_beat") for ps in first_window)
    modalities = {"verbal": has_verbal, "visual": has_visual, "audio": has_audio}
    for req in hook_requires:
        if not modalities.get(req, False):
            return False, f"missing hook modality: {req}"
    return True, f"hook satisfied ({', '.join(hook_requires)} present in first {hook_window}s)"


def _find_pacing_violations(segments: list[dict], profile: dict) -> list[str]:
    violations: list[str] = []
    kept = [s for s in segments if s["keep"]]
    if not kept:
        return ["no segments kept"]
    consecutive_long = 0
    for s in kept:
        if s["end"] - s["start"] > profile["pattern_interrupt_max"]:
            consecutive_long += 1
            if consecutive_long >= 2:
                violations.append(f"two consecutive long segments (> {profile['pattern_interrupt_max']}s each) at t={s['start']:.1f}s")
                break
        else:
            consecutive_long = 0
    short_count = sum(1 for s in kept if (s["end"] - s["start"]) < profile["pattern_interrupt_min"])
    if short_count > len(kept) * 0.3:
        violations.append(f"{short_count} of {len(kept)} segments shorter than min interrupt ({profile['pattern_interrupt_min']}s) — choppy")
    return violations
